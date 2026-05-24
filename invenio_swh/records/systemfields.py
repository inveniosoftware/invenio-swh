# SPDX-FileCopyrightText: 2024-2025 CERN.
# SPDX-License-Identifier: MIT
"""Software Heritage system fields."""

from invenio_records.systemfields import SystemField

from invenio_swh.api import SWHDeposit


class SWHObj:
    """Software Heritage object.

    Implements logic around accessing the SWH object and dumping it.
    """

    def __init__(self, record, deposit=None):
        """Initialise the SWH object."""
        self._record = record
        self._deposit = deposit

    @property
    def deposit(self):
        """Get the deposit object."""
        return self._deposit or SWHDeposit.get_by_record_id(str(self._record.id))

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

    def obj(self, record):
        """Initialise the object, or load it from record's cache."""
        obj_cache = getattr(record, "_obj_cache", None)
        if obj_cache is not None and self.attr_name in obj_cache:
            return obj_cache[self.attr_name]

        obj = SWHObj(record)
        return obj

    def post_dump(self, record, data, dumper=None):
        """Called after the record is dumped in secondary storage."""
        obj = self.obj(record)
        val = obj.dump()
        if val:
            data[self.key] = val

    def post_load(self, record, data, loader=None):
        """Execute after a record was loaded."""
        record.pop(self.key, None)
        swh_data = data.pop(self.key, None)
        swh = None
        if swh_data:
            deposit = SWHDeposit.load(swh_data)
            swh = SWHObj(record, deposit=deposit)
        self._set_cache(record, swh)
