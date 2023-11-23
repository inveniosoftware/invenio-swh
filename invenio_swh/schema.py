# -*- coding: utf-8 -*-
#
# Copyright (C) 2023 CERN.
#
# Invenio-RDM is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.
"""Invenio-SWH service schema."""

from invenio_rdm_records.resources.serializers.codemeta import CodemetaSchema


class SWHCodemetaSchema(CodemetaSchema):
    """Subset of Codemeta schema for Software Heritage."""

    class Meta:
        """Meta class, defines subset of fields to be dumped."""

        fields = (
            "name",
            "author",
            "datePublished",
            "license",
            "description",
            "version",
            "codeRepository",
            "runtimePlatform",
            "programmingLanguage",
            "operatingSystem",
            "developmentStatus",
        )
