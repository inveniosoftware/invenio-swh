# SPDX-FileCopyrightText: 2020 CERN
# SPDX-FileCopyrightText: 2020 Cottage Labs LLP.
# SPDX-License-Identifier: MIT

"""Module tests."""

from flask import Flask

from invenio_swh import InvenioSWH


def test_version():
    """Test version import."""
    from invenio_swh import __version__

    assert __version__


def test_init():
    """Test extension initialization."""
    app = Flask("testapp")
    app.config.update(
        {
            "SWH_SERVICE_DOCUMENT": "test",
            "SWH_USERNAME": "test",
            "SWH_PASSWORD": "test",
            "SWH_ACCEPTED_EXTENSIONS": "test",
            "SWH_ACCEPTED_RECORD_TYPES": "test",
            "SWH_ENABLED": "test",
        }
    )
    ext = InvenioSWH(app)
    assert "invenio-swh" in app.extensions

    # Extension not configured, therefore not initialized.
    app = Flask("testapp")
    ext = InvenioSWH(app)
    assert "invenio-swh" not in app.extensions
