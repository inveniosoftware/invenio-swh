# -*- coding: utf-8 -*-
#
# Copyright (C) 2023 CERN.
#
# Invenio-RDM is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.
"""API representation of a Software Heritage deposit."""

from invenio_db import db

from invenio_swh.models import SWHDepositModel


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

    @classmethod
    def get(cls, id_):
        """Get a swh deposit by id."""
        with db.session.no_autoflush:
            query = cls.model_cls.query.filter_by(swh_deposit_id=str(id_))
            deposit = query.one()
            return cls(deposit)

    @classmethod
    def get_by_status(cls, status):
        """Get a swh deposit by status."""
        with db.session.no_autoflush:
            query = cls.model_cls.query.filter_by(status=status)
            return [cls(deposit) for deposit in query.all()]

    @classmethod
    def get_record_deposit(cls, record_id):
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

    @property
    def swhid(self):
        """Returns the software hash id of the swh deposit."""
        return self.model.swhid

    @property
    def status(self):
        """Returns the status of the swh deposit."""
        return self.model.status

    def commit(self):
        """Commit the deposit to the database."""
        if self.model is None:
            return

        with db.session.begin_nested():
            res = db.session.merge(self.model)
            self.model = res
        return self
