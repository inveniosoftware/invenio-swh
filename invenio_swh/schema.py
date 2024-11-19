# -*- coding: utf-8 -*-
#
# Copyright (C) 2023-2024 CERN.
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
