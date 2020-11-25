# -*- coding: utf-8 -*-
#
# Copyright (C) 2020 CERN
# Copyright (C) 2020 Cottage Labs LLP.
#
# invenio-swh is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Support for onward deposit of software artifacts to Software Heritage"""

from .ext import InvenioSWH
from .version import __version__

__all__ = ('__version__', 'InvenioSWH')
