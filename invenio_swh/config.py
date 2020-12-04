# -*- coding: utf-8 -*-
#
# Copyright (C) 2020 CERN
# Copyright (C) 2020 Cottage Labs LLP.
#
# invenio-swh is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Support for onward deposit of software artifacts to Software Heritage"""


INVENIO_SWH_BASE_TEMPLATE = 'invenio_swh/base.html'
"""Default base template for the demo page."""

INVENIO_SWH_SERVICES = {
    'swh': {
        'NAME': "Software Heritage",
        'SERVICE_DOCUMENT': 'https://deposit.softwareheritage.org/1/servicedocument/',
        'USERNAME': None,
        'PASSWORD': None,
    }
}
