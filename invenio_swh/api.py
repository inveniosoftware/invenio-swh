# -*- coding: utf-8 -*-
#
# Copyright (C) 2023 CERN.
#
# Invenio-RDM is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.
"""API representation of a Software Heritage deposit."""

from invenio_db import db
from invenio_rdm_records.proxies import current_rdm_records_service as record_service
from werkzeug.utils import cached_property

from invenio_swh.models import SWHDepositModel, SWHDepositStatus


class SWHDeposit:
    """API abstraction of a Software Heritage deposit.

    This class provides an abstraction layer for interacting with Software Heritage deposits.
    It encapsulates the functionality for creating, retrieving, and managing deposits.

    Attributes
    ----------
        model_cls (class): The model class associated with the deposit.
        model (object): The instance of the model associated with the deposit.

    """

    model_cls = SWHDepositModel

    def __init__(self, model=None):
        """Instantiate deposit object."""
        self.model = model

    @classmethod
    def create(cls, object_uuid):
        """Create a new swh deposit."""
        with db.session.no_autoflush:
            deposit = cls.model_cls(object_uuid=object_uuid)
            return cls(deposit)

    @cached_property
    def origin(self):
        """Return the origin of the deposit."""
        records_ids = self.record_cls.get_records_by_parent(
            self.record.parent, with_deleted=True, ids_only=True
        )
        for record_id in records_ids:
            deposit = SWHDeposit.get_by_record_id(record_id)
            if deposit.model and deposit.status == SWHDepositStatus.SUCCESS:
                return self.record.parent
        return None

    @property
    def record_cls(self):
        """Return the record class associated with the deposit."""
        return record_service.record_cls

    @cached_property
    def record(self):
        """Return the record associated with the deposit."""
        return self.record_cls.get_record(self.model.object_uuid)

    @classmethod
    def get(cls, id_):
        """Get a swh deposit by id."""
        with db.session.no_autoflush:
            query = cls.model_cls.query.filter_by(swh_deposit_id=str(id_))
            deposit = query.one()
            return cls(deposit)

    @classmethod
    def get_by_record_id(cls, record_id):
        """Get a local swh deposit by record id."""
        with db.session.no_autoflush:
            deposit = cls.model_cls.query.filter_by(object_uuid=record_id).one_or_none()
            return cls(deposit)

    @property
    def record_id(self):
        """Returns the UUID of the object associated with the record."""
        return self.model.object_uuid

    @property
    def id(self):
        """Returns the remote id of the swh deposit."""
        return self.model.swh_deposit_id

    @id.setter
    def id(self, value):
        """Set the remote id of the swh deposit."""
        self.model.swh_deposit_id = value

    @property
    def swhid(self):
        """Returns the software hash id of the swh deposit."""
        return self.model.swhid

    @swhid.setter
    def swhid(self, value):
        """Set the software hash id of the swh deposit."""
        self.model.swhid = value

    @property
    def status(self):
        """Returns the status of the swh deposit."""
        return self.model.status

    @status.setter
    def status(self, value):
        """Set the status of the swh deposit."""
        if isinstance(value, str) and value in [x.item for x in SWHDepositStatus]:
            self.model.status = SWHDepositStatus(value)
        elif isinstance(value, SWHDepositStatus):
            self.model.status = value
        else:
            raise ValueError(
                f"Invalid status value for Software Heritage deposit. Got: {value}"
            )

    def commit(self):
        """Commit the deposit to the database."""
        if self.model is None:
            return

        with db.session.begin_nested():
            res = db.session.merge(self.model)
            self.model = res
        return self
