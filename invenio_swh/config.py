# -*- coding: utf-8 -*-
#
# Copyright (C) 2023 CERN
# Copyright (C) 2020 Cottage Labs LLP.
#
# invenio-swh is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Support for onward deposit of software artifacts to Software Heritage."""


SWH_ENABLED = False
"""Enable/disable the extension."""

SWH_SERVICE_DOCUMENT = "https://deposit.staging.swh.network/1"
"""Software Heritage service document IRI."""

SWH_USERNAME = ""
"""Software Heritage username."""

SWH_PASSWORD = ""
"""Software Heritage password."""

SWH_COLLECTION_IRI = "https://deposit.staging.swh.network/1/inveniordm/"
"""Software Heritage collection IRI where to archive deposits."""

SWH_UI_BASE_URL = "https://webapp.staging.swh.network"
"""Software Heritage UI base URL."""

SWH_ACCEPTED_EXTENSIONS = {"zip", "tar", "tar.gz", "tar.bz2", "tar.lzma"}
"""Accepted file extensions to deposit in Software Heritage."""

SWH_ACCEPTED_RECORD_TYPES = {"software"}
"""Accepted record types to deposit in Software Heritage."""

SWH_RATE_LIMIT = "20/m"
"""Rate limit for the Software Heritage API."""

SWH_MAX_FILE_SIZE = 100 * 1024 * 1024
"""Maximum file size to deposit in Software Heritage."""
