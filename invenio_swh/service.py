# -*- coding: utf-8 -*-
#
# Copyright (C) 2023 CERN.
#
# Invenio-swh is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.
"""Invenio Software Heritage service."""

from flask import current_app
from invenio_records_resources.services.uow import RecordCommitOp, unit_of_work

from invenio_swh.api import SWHDeposit
from invenio_swh.controller import SWHController
from invenio_swh.errors import DepositFailed, DepositNotCreated, InvalidRecord
from invenio_swh.models import SWHDepositStatus
from invenio_swh.schema import SWHCodemetaSchema


class SWHDepositResult(object):
    """Single SWHDeposit result."""

    def __init__(self, deposit: SWHDeposit) -> None:
        """Instantiate result item."""
        self.deposit = deposit


class SWHService(object):
    """Invenio Software Heritage service."""

    SWH_STATUS_MAP = {
        "deposited": SWHDepositStatus.WAITING,
        "verified": SWHDepositStatus.WAITING,
        "partial": SWHDepositStatus.WAITING,
        "loading": SWHDepositStatus.WAITING,
        "rejected": SWHDepositStatus.FAILED,
        "expired": SWHDepositStatus.FAILED,
        "failed": SWHDepositStatus.FAILED,
        "done": SWHDepositStatus.SUCCESS,
    }
    """Map of SWH statuses to internal statuses."""

    @property
    def schema(self):
        """Service schema."""
        return SWHCodemetaSchema()

    @property
    def record_cls(self):
        """Record class."""
        return SWHDeposit

    @property
    def result_cls(self):
        """Result item class."""
        return SWHDepositResult

    def result_item(self, deposit: SWHDeposit):
        """Return a result item."""
        return self.result_cls(deposit)

    def __init__(self, controller: SWHController):
        """Instantiate the service.

        Injects the software heritage controller into the service.
        """
        self.controller = controller

    @unit_of_work()
    def create(self, record, uow=None):
        """Create a new deposit.

        If the controller fails to create the deposit, it won't be created locally either.
        """
        self.validate_record(record)

        metadata = self.schema.dump(record)
        swh_deposit = self.controller.create_deposit(metadata)
        deposit_id = swh_deposit.get("deposit_id")
        if not deposit_id:
            raise DepositNotCreated("Deposit id not returned by SWH.")

        deposit = self.record_cls.create(record.id)
        deposit.id = str(deposit_id)
        self.update_status(deposit, SWHDepositStatus.CREATED, uow=uow)

        uow.register(RecordCommitOp(deposit))
        return deposit

    def get_record_deposit(self, record_id):
        """Return the deposit associated to a given record."""
        deposit = self.record_cls.get_by_record_id(record_id)
        return self.result_item(deposit)

    def read(self, id_) -> SWHDepositResult:
        """Read a deposit given its id."""
        deposit = self.record_cls.get(id_)
        return self.result_item(deposit)

    @unit_of_work()
    def sync_status(self, id_, uow=None):
        """Synchronize local state with external source (SWH)."""
        deposit_res = self.read(id_)
        deposit = deposit_res.deposit
        if not deposit:
            return
        res = self.controller.fetch_deposit_status(deposit.id)
        new_status = res.get("deposit_status")
        self.update_status(deposit, new_status)

        # Handle swhid created
        swhid = res.get("deposit_swhid")
        if swhid and not deposit.swhid:
            self.update_swhid(deposit.id, swhid, uow=uow)
        return self.result_item(deposit)

    @unit_of_work()
    def complete(self, id_: int, uow=None):
        """Complete a deposit.

        :param id_: The ID of the deposit to complete.
        :type id_: int
        :param uow: The unit of work.
        :type uow: Union[UnitOfWork, None]
        :return: The completed deposit.
        :rtype: Deposit
        :raises DepositFailed: If the deposit has already failed.
        """
        deposit_res = self.read(id_)
        deposit = deposit_res.deposit
        if deposit.status == SWHDepositStatus.FAILED:
            raise DepositFailed(
                "Deposit has already failed. Cannot complete deposition."
            )
        try:
            self.controller.complete_deposit(deposit.id)
            self.update_status(deposit, SWHDepositStatus.WAITING, uow=uow)
        except Exception as exc:
            current_app.logger.exception("Deposit completion failed.")
            self.update_status(deposit, SWHDepositStatus.FAILED, uow=uow)
        return deposit

    @unit_of_work()
    def upload_files(self, id_, files, uow=None):
        """Upload files to a deposit.

        ``files``` are the representation of the files to be uploaded. It is an API instance of the RDM record files.

        The files are first normalized by the service, assuring that the file(s) to be sent are compatible with the current
        implementation of the integration.

        :param id_: The ID of the deposit.
        :type id_: int
        :param files: The files to be uploaded.
        :type files: RecordFiles
        :param uow: The unit of work.
        :type uow: object, optional
        :return: The updated deposit.
        :rtype: object
        """
        deposit_res = self.read(id_)
        deposit = deposit_res.deposit
        try:
            self.validate_files(files)
            file = self._get_first_file(files)
            fp = file.get_stream("rb")
            file_metadata = file.file.dumps()
            file_metadata["filename"] = file.file.key
            self.controller.update_deposit_files(deposit.id, fp, file_metadata)
        except Exception as exc:
            current_app.logger.exception(str(exc))
            self.update_status(deposit, SWHDepositStatus.FAILED, uow=uow)
        return deposit

    @unit_of_work()
    def update_swhid(self, id_: int, swhid: str, uow=None) -> None:
        """Update the SWHID and status of a deposit.

        The deposit is considered to be "SUCCESS" if the SWHID is successfully updated.

        :param id_: The ID of the deposit.
        :type id_: int
        :param swhid: The new SWHID to be assigned to the deposit.
        :type swhid: str
        :param uow: The unit of work to register the operation with. (optional)
        :type uow: object, default=None
        :return: The updated deposit.
        :rtype: object
        """
        deposit_res = self.read(id_)
        deposit = deposit_res.deposit
        try:
            deposit.swhid = swhid
            self.update_status(deposit, SWHDepositStatus.SUCCESS, uow=uow)
            uow.register(RecordCommitOp(deposit))
        except Exception as exc:
            current_app.logger.exception(str(exc))
            self.update_status(deposit, SWHDepositStatus.FAILED, uow=uow)

        return deposit

    def _parse_status(self, status):
        """Parse the status to an internal status.

        :param status: The status to be parsed.
        :type status: str or SWHDepositStatus
        """
        if isinstance(status, str):
            return self.SWH_STATUS_MAP.get(status)
        if isinstance(status, SWHDepositStatus):
            return status
        raise ValueError(f"Invalid status: {status}")

    @unit_of_work()
    def update_status(self, deposit: SWHDeposit, status, uow=None):
        """Handle a status update of the deposit.

        It can be used to update the status from the remote, by parsing the status to an internal status.
        It can also be used to update the status to a new one.

        :param deposit: The deposit to be updated.
        :type deposit: SWHDeposit
        :param status: The new status of the deposit.
        :type status: str or SWHDepositStatus
        :param uow: The unit of work.

        """
        internal_status = self._parse_status(status)
        # Update the status if it has changed
        if deposit.status != internal_status:
            deposit.status = internal_status
            uow.register(RecordCommitOp(deposit))

    def _get_first_file(self, files_manager):
        fname = list(files_manager.entries.keys())[0]
        fdata = files_manager.entries[fname]
        return fdata

    def validate_record(self, record):
        """Check whether the record can be sent to Software Heritage.

        Checks the following:
        - Record type is of a valid one
        - Record files are valid
        - Record is fully open

        :param record: The record to be validated
        :type record: RDMRecord
        """
        # Check resource type
        resource_type = record.get("metadata", {}).get("resource_type", {}).get("id")
        valid_types = current_app.config["SWH_ACCEPTED_RECORD_TYPES"]
        if resource_type not in valid_types:
            raise InvalidRecord(f"Record is not of valid type: {str(valid_types)}")

        self.validate_files(record.files)

        # Check access rights
        is_open = (
            record.access.protection.record == "public"
            and record.access.protection.files == "public"
        )
        if not is_open:
            raise InvalidRecord(
                f"Only fully open records are allowed to be sent to Software Heritage."
            )

        return True

    def validate_files(self, files):
        """Validate files to be sent to Software Heritage.

        Checks the following:
        - Record only has one file and it is of a valid extension
        - Record file is not too big
        """
        # Check number of files
        if not len(files) == 1:
            current_app.logger.warning(
                "Software Heritage integration only enabled for one file."
            )
            raise InvalidRecord("Integration only accepts one file.")

        # Check file extension
        fname = list(files.entries.keys())[0]
        fdata = files.entries[fname]

        valid_extensions = current_app.config["SWH_ACCEPTED_EXTENSIONS"]

        if fdata.file.ext not in valid_extensions:
            raise InvalidRecord(f"File is not of valid type: {str(valid_extensions)}")

        # Check file size
        max_size = current_app.config["SWH_MAX_FILE_SIZE"]
        if fdata.file.size > max_size:
            raise InvalidRecord(f"File is too big: {max_size}")

        return fdata
