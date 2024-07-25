# -*- coding: utf-8 -*-
#
# Copyright (C) 2024 CERN.
#
# Invenio-SWH is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.
"""Software Heritage system fields."""

from invenio_records.systemfields import SystemField
from werkzeug.utils import cached_property

from invenio_swh.api import SWHDeposit
from invenio_swh.proxies import current_swh_ext


class SWHObj(object):
    """Software Heritage object.

    Implements logic around accessing the SWH object and dumping it.
    """

    def __init__(self, record):
        """Initialise the SWH object."""
        self._record = record

    @cached_property
    def deposit(self):
        """Get the deposit object."""
        return SWHDeposit.get_by_record_id(str(self._record.id))

    def dump(self):
        """Dump the SWH object."""
        if self.deposit and self.deposit.swhid:
            return {
                "swhid": self.deposit.swhid,
            }
        return None

    def __getattr__(self, name):
        """Get attribute from deposit."""
        attr = getattr(self.deposit, name, None)
        if not attr:
            raise AttributeError(f"Attribute {name} not found in SWHObj")
        return attr


class SWHSysField(SystemField):
    """Software Heritage system field."""

    def __init__(self, key="swh"):
        """Initialise the software hash id field."""
        super().__init__(key)

    def __get__(self, record, owner=None):
        """Get the SWH object."""
        if record is None:
            # access by class
            return self

        # access by object
        return self.obj(record)

    def __set__(self, record, obj):
        """Set the SWH object."""
        self.set_obj(record, obj)

    def obj(self, record):
        """Initialise the object, or load it from record's cache."""
        obj = self._get_cache(record)
        if obj is not None:
            return obj
        obj = SWHObj(record)
        return obj

    def set_obj(self, record, swh):
        """Set the object in the record's cache."""
        assert isinstance(swh, SWHObj)
        self._set_cache(record, swh)

    def post_dump(self, record, data, dumper=None):
        """Execute after the record was dumped in secondary storage."""
        obj = self.obj(record)
        val = obj.dump()
        if val:
            data[self.key] = val

    def post_load(self, record, data, loader=None):
        """Execute after a record was loaded."""
        if self.key in data:
            record[self.key] = data[self.key]
