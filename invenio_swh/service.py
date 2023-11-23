# -*- coding: utf-8 -*-
#
# Copyright (C) 2023 CERN.
#
# Invenio-swh is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.
"""Invenio Software Heritage service."""

from collections.abc import Iterable

from flask import current_app
from invenio_rdm_records.proxies import current_rdm_records_service as record_service
from invenio_records_resources.services.uow import RecordCommitOp, unit_of_work

from invenio_swh.api import SWHDeposit
from invenio_swh.controller import SWHController
from invenio_swh.errors import DepositFailed, InvalidRecord
from invenio_swh.models import SWHDepositStatus
from invenio_swh.schema import SWHCodemetaSchema


class SWHDepositResult(object):
    """Single WHDeposit result."""

    def __init__(self, deposit: SWHDeposit) -> None:
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
        """Returns a result item."""
        return self.result_cls(deposit)

    def __init__(self, swh_controller: SWHController):
        """Constructor.

        Injects the software heritage controller into the service.
        """
        self.swh_controller = swh_controller

    @unit_of_work()
    def create(self, record, uow=None):
        """Creates a new deposit.

        If the controller fails to create the deposit, the transaction will be rolledback by the Unit of Work
        and the deposit won't be created locally.
        """
        self.validate_record(record)

        deposit = self.record_cls.create(record.id)

        metadata = self.schema.dump(record)
        swh_deposit = self.swh_controller.create_deposit(metadata)
        deposit.model.swh_deposit_id = int(swh_deposit["deposit_id"])
        deposit.model.status = SWHDepositStatus.CREATED

        uow.register(RecordCommitOp(deposit))
        return deposit

    def get_record_deposit(self, record_id):
        deposit = self.record_cls.get_record_deposit(record_id)
        return self.result_item(deposit)

    def read(self, id_) -> SWHDepositResult:
        deposit = self.record_cls.get(id_)
        return self.result_item(deposit)

    @unit_of_work()
    def sync_status(self, id_, uow=None):
        """Synchronizes local state with external source (SWH)."""
        deposit_res = self.read(id_)
        deposit = deposit_res.deposit
        if not deposit:
            return
        res = self.swh_controller.fetch_deposit_status(deposit.id)
        new_status = res.get("deposit_status")
        if new_status in ("failed", "rejected", "expired"):
            current_app.logger.warning("Deposit failed")
            current_app.logger.warning(str(res))
        self._handle_status_update(deposit, new_status)

        # Handle swhid created
        swhid = res.get("deposit_swhid")
        if swhid and not deposit.swhid:
            self.update_swhid(deposit.id, swhid, uow=uow)
        return self.result_item(deposit)

    @unit_of_work()
    def complete(self, id_: int, uow=None):
        try:
            deposit_res = self.read(id_)
            deposit = deposit_res.deposit
            if deposit.status == SWHDepositStatus.FAILED:
                raise DepositFailed("Deposit can't be completed, already failed.")

            self.swh_controller.complete_deposit(deposit.id)
            deposit.model.status = SWHDepositStatus.WAITING
        except Exception as exc:
            current_app.logger.exception(str(exc))
            deposit.model.status = SWHDepositStatus.FAILED
        uow.register(RecordCommitOp(deposit))
        return deposit

    @unit_of_work()
    def upload_files(self, id_, files, uow=None):
        try:
            deposit_res = self.read(id_)
            deposit = deposit_res.deposit
            if deposit.status == SWHDepositStatus.FAILED:
                raise DepositFailed("Deposit can't receive new files, already failed.")

            file = self._normalize_files(files.entries.values())
            fp = file.get_stream("rb")
            file_metadata = file.file.dumps()
            file_metadata["filename"] = file.file.key
            self.swh_controller.update_deposit_files(deposit.id, fp, file_metadata)
        except Exception as exc:
            current_app.logger.exception(str(exc))
            deposit.model.status = SWHDepositStatus.FAILED
            uow.register(RecordCommitOp(deposit))
        return deposit

    @unit_of_work()
    def update_swhid(self, id_: int, swhid: str, uow=None) -> None:
        try:
            deposit_res = self.read(id_)
            deposit = deposit_res.deposit
            deposit.model.swhid = swhid
            deposit.model.status = SWHDepositStatus.SUCCESS
        except Exception as exc:
            current_app.logger.exception(str(exc))
            deposit.model.status = SWHDepositStatus.FAILED

        uow.register(RecordCommitOp(deposit))
        return deposit

    @unit_of_work()
    def _handle_status_update(self, deposit: SWHDeposit, status: str, uow=None):
        internal_status = self.SWH_STATUS_MAP.get(status)
        if not internal_status:
            current_app.logger.warning(
                f"Got unkwnown deposit status from remote: {status}"
            )
            return
        if deposit.model.status != internal_status:
            deposit.model.status = internal_status
            uow.register(RecordCommitOp(deposit))

    def _normalize_files(self, files):
        # Assumes only file for now
        if not isinstance(files, list) and isinstance(files, Iterable):
            files = list(files)

        # TODO only accepts one file for now
        return files[0]

    def validate_record(self, record):
        """Checks whether the record can be sent to Software Heritage."""
        # Check resource type
        resource_type = record.get("metadata", {}).get("resource_type", {}).get("id")
        valid_types = current_app.config["SWH_ACCEPTED_RECORD_TYPES"]
        if not resource_type in valid_types:
            raise InvalidRecord(f"Record is not of valid type: {str(valid_types)}")

        # Check files
        if not len(record.files) == 1:
            current_app.logger.warning(
                "Software Heritage integration only enabled for one file."
            )
            raise InvalidRecord("Integration only accepts one file.")

        # Check file extension
        fname = list(record.files.entries.keys())[0]
        fdata = record.files.entries[fname]

        valid_extensions = current_app.config["SWH_ACCEPTED_EXTENSIONS"]

        if not fdata.file.ext in valid_extensions:
            raise InvalidRecord(f"File is not of valid type: {str(valid_extensions)}")

        # Check file size
        max_size = current_app.config["SWH_MAX_FILE_SIZE"]
        if fdata.file.size > max_size:
            raise InvalidRecord(f"File is too big: {max_size}")

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
