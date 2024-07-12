# -*- coding: utf-8 -*-
#
# Copyright (C) 2023 CERN.
#
# Invenio-swh is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.
"""Databatase models for software heritage integration."""

from enum import Enum

from invenio_db import db
from sqlalchemy_utils import Timestamp
from sqlalchemy_utils.types import ChoiceType, UUIDType


class SWHDepositStatus(Enum):
    """Constants for possible status of a Release."""

    __order__ = "NEW CREATED WAITING SUCCESS FAILED"

    NEW = "N"
    """Deposit was created locally."""

    CREATED = "C"
    """Deposit was created in remote, not yet complete."""

    WAITING = "W"
    """Deposit was completed and it's waiting SWH loading."""

    SUCCESS = "S"
    """Deposit was successfully loaded by Software Heritage."""

    FAILED = "F"
    """Deposit was failed to be loaded by Software Heritage."""


class SWHDepositModel(db.Model, Timestamp):
    """Model for a Software Heritage deposit."""

    # Enables SQLAlchemy version counter (not the same as SQLAlchemy-Continuum)

    __tablename__ = "swh_deposit"

    version_id = db.Column(db.Integer, nullable=False)
    """Used by SQLAlchemy for optimistic concurrency control."""

    __mapper_args__ = {"version_id_col": version_id}

    object_uuid = db.Column(UUIDType, primary_key=True)
    """Object ID - e.g. a record id."""

    swhid = db.Column(db.String(1024), nullable=True)
    """Software Hash ID."""

    swh_deposit_id = db.Column(db.String, nullable=True)
    """Software Heritage deposit id."""

    status = db.Column(
        ChoiceType(SWHDepositStatus, impl=db.CHAR(1)),
        nullable=False,
        index=True,
        default=SWHDepositStatus.NEW,
    )
    """Deposit status. It is indexed to improve the search of deposits that e.g failed."""

    def __repr__(self):
        """String representation of a SWHDeposit."""
        return f"<SWHDepositModel(deposit_id={self.swh_deposit_id}, object_uuid={self.object_uuid}, status={self.status})>"
