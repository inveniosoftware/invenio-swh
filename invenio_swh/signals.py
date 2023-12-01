# -*- coding: utf-8 -*-
#
# Copyright (C) 2023 CERN.
#
# Invenio-SWH is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.
"""Software heritage signals."""

from invenio_swh.tasks import process_published_record


def post_publish_receiver(sender, pid=None, **kwargs):
    """Signal receiver for post-publish signal."""
    process_published_record.si(pid).apply(throw=True)
