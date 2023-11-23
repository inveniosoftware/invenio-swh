# -*- coding: utf-8 -*-
#
# Copyright (C) 2023 CERN.
#
# Invenio-RDM is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.
"""Proxy objects of invenio-swh."""
from flask import current_app
from werkzeug.local import LocalProxy

current_swh_ext = LocalProxy(lambda: current_app.extensions["invenio-swh"])
"""Helper proxy to access SWH extension object."""

current_swh_service = LocalProxy(lambda: current_app.extensions["invenio-swh"].service)
"""Helper proxy to access the SWH service. """
