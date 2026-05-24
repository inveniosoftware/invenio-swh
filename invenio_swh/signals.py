# SPDX-FileCopyrightText: 2023 CERN.
# SPDX-License-Identifier: MIT
"""Software heritage signals."""

from invenio_swh.tasks import process_published_record


def post_publish_receiver(sender, pid=None, **kwargs):
    """Signal receiver for post-publish signal."""
    process_published_record.si(pid).apply(throw=True)
