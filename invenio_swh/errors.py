# -*- coding: utf-8 -*-
#
# Copyright (C) 2023 CERN.
#
# Invenio-swh is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.
"""Invenio / Software Heritage errors."""


class InvenioSWHException(Exception):
    """Base exception for Invenio-SWH."""


class InvalidRecord(InvenioSWHException):
    """Triggered when the record is not valid to be sent to Software Heritage.

    Examples of an invalid record: record is not fully open (files + metadata).
    """


class ClientException(Exception):
    """Generic implementation of a client exception (e.g. request failed on remote)."""


class DepositWaiting(InvenioSWHException):
    """Raised when the deposit status is "waiting"."""


class DepositFailed(InvenioSWHException):
    """Raised when the deposit status is "failed"."""


####
# Controller exceptions
####
class ControllerException(InvenioSWHException):
    """Generic implementation of a controller exception (e.g. request failed on remote)."""


class DeserializeException(ControllerException):
    """Raised when a remote response failed to be deserialized."""
