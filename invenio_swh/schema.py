# -*- coding: utf-8 -*-
#
# Copyright (C) 2023 CERN.
#
# Invenio-RDM is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.
"""Invenio-SWH service schema."""
from flask import current_app
from invenio_rdm_records.contrib.codemeta.processors import CodemetaDumper
from invenio_rdm_records.resources.serializers.codemeta import CodemetaSchema
from marshmallow import fields


class SWHCodemetaSchema(CodemetaSchema):
    """Subset of Codemeta schema for Software Heritage."""

    deposit = fields.Method("add_deposit_info", data_key="swh:deposit")

    def __init__(self, *args, **kwargs):
        """Instantiate Codemeta schema adapted to Software Heritage.

        Injects the codemeta dumper into the schema processors.
        """
        kw = {**kwargs, "dumpers": [CodemetaDumper()]}
        super().__init__(*args, **kw)

    class Meta:
        """Meta class, defines subset of fields to be dumped."""

        fields = (
            "identifier",
            "name",
            "author",
            "datePublished",
            "license",
            "description",
            "version",
            "codeRepository",
            "programmingLanguage",
            "developmentStatus",
            "deposit",
        )

    def add_deposit_info(self, obj):
        """Add deposit information to the codemeta."""
        if hasattr(obj, "parent"):
            parent_record = obj.parent
        else:
            parent_record = obj["parent"]

        parent_doi = parent_record.get("pids", {}).get("doi")["identifier"]
        origin_obj = {"swh:origin": {"@url": f"https://doi.org/{parent_doi}"}}

        # If the record is the first version, it dumps `create_origin`
        # Otherwise, dumps `add_to_origin`
        is_first_version = obj.versions.index == 1
        ret = {}
        if is_first_version:
            ret["swh:create_origin"] = origin_obj
        else:
            ret["swh:add_to_origin"] = origin_obj
        return ret
