# -*- coding: utf-8 -*-
#
# Copyright (C) 2024 CERN.
#
# Invenio-SWH is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.
""" TODO """

from invenio_records.systemfields import SystemField
from werkzeug.utils import cached_property

from invenio_swh.api import SWHDeposit
from invenio_swh.proxies import current_swh_ext


class SWHObj(object):

    def __init__(self, record):
        self._record = record

    @cached_property
    def deposit(self):
        """Get the deposit object."""
        return SWHDeposit.get_by_record_id(str(self._record.id))

    def dump(self):
        return self.deposit.swhid if self.deposit else None

    def __getattr__(self, name):
        # Try to get from attribute from deposit first, e.g. record.swh.swhid
        attr = getattr(self.deposit, name, None)
        if not attr:
            raise AttributeError(f"Attribute {name} not found in SWHObj")
        return attr


class SWHSysField(SystemField):
    def __init__(self, key):
        """Initialise the versions field."""
        super().__init__(key)

    def __get__(self, record, owner=None):
        """Get the record's access object."""
        if record is None:
            # access by class
            return self

        # access by object
        return self.obj(record)

    def __set__(self, record, obj):
        """Set the records access object."""
        self.set_obj(record, obj)

    def obj(self, record):
        """Get the version manager."""
        obj = self._get_cache(record)
        if obj is not None:
            return obj
        obj = SWHObj(record)
        return obj

    def set_obj(self, record, swh):
        """Set an version manager on the record."""
        assert isinstance(swh, SWHObj)
        self._set_cache(record, swh)

    def post_dump(self, record, data, dumper=None):
        """Execute after the record was dumped in secondary storage."""
        obj = self.obj(record)
        val = obj.dump()
        if val:
            data[self.key] = val

        # Cache the object in record
        self.set_obj(record, obj)

    def pre_load(self, data, loader=None):
        """Execute before a record is loaded from secondary storage."""
        # Cache the object in record
        pass

    def post_load(self, record, data, loader=None):
        """Execute after a record was loaded."""
        # look for alternate_identifiers and load the obj from there
        identifiers = data.get("metadata", {}).get("identifiers", [])

        # It should be cached at this point
        obj = self.obj(record)

        # Add to record.alternate_identifiers
        swhid = obj.dump()
        if swhid:
            identifiers.append(
                {"scheme:": "swh", "identifier": swhid}
            )
            record["metadata"]["identifiers"] = identifiers
            pass

class SWHExtension(object):
    swhid = SWHSysField("swhid")


def add_swh_extension(app, record_cls):
    # generate a new class with the field and return it
    if current_swh_ext.is_enabled(app) and current_swh_ext.is_configured(app):
        return type(record_cls.__name__, (record_cls, SWHExtension), {})
    return record_cls
