# -*- coding: utf-8 -*-
#
# Copyright (C) 2020 CERN
# Copyright (C) 2020 Cottage Labs LLP.
#
# invenio-swh is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Pytest configuration.

See https://pytest-invenio.readthedocs.io/ for documentation on which test
fixtures are available.
"""
from collections import namedtuple

import pytest
from flask_principal import Identity, Need, UserNeed
from invenio_access.permissions import system_identity
from invenio_app.factory import create_api as _create_api
from invenio_vocabularies.proxies import current_service as vocabulary_service
from invenio_vocabularies.records.api import Vocabulary
from mock import MagicMock
from invenio_swh.proxies import current_swh_service


@pytest.fixture(scope="module")
def create_app(instance_path, entry_points):
    """Application factory fixture."""
    return _create_api


@pytest.fixture(scope="module")
def app_config(app_config):
    """Application configuration fixture."""
    app_config["SWH_ENABLED"] = True
    return app_config


RunningApp = namedtuple(
    "RunningApp",
    [
        "app",
        "superuser_identity",
        "location",
        "cache",
        "resource_type_v",
    ],
)


@pytest.fixture
def running_app(
    app,
    superuser_identity,
    location,
    cache,
    resource_type_v,
):
    """This fixture provides an app with the typically needed db data loaded.

    All of these fixtures are often needed together, so collecting them
    under a semantic umbrella makes sense.
    """
    return RunningApp(
        app,
        superuser_identity,
        location,
        cache,
        resource_type_v,
    )


@pytest.fixture(scope="function")
def minimal_record(users):
    """Minimal record data as dict coming from the external world."""
    return {
        "access": {
            "record": "public",
            "files": "public",
        },
        "files": {"enabled": False},  # Most tests don't care about file upload
        "metadata": {
            "publication_date": "2020-06-01",
            "resource_type": {
                "id": "image-photo",
            },
            # Technically not required
            "creators": [
                {
                    "person_or_org": {
                        "type": "personal",
                        "name": "Doe, John",
                        "given_name": "John Doe",
                        "family_name": "Doe",
                    }
                }
            ],
            "title": "A Romans story",
        },
    }


@pytest.fixture(scope="module")
def identity_simple():
    """Simple identity fixture."""
    i = Identity(1)
    i.provides.add(UserNeed(1))
    i.provides.add(Need(method="system_role", value="authenticated_user"))
    i.provides.add(Need(method="system_role", value="any_user"))
    return i


@pytest.fixture(scope="module")
def resource_type_type(app):
    """Resource type vocabulary type."""
    return vocabulary_service.create_type(system_identity, "resource_types", "rsrct")


@pytest.fixture(scope="module")
def resource_type_v(app, resource_type_type):
    """Resource type vocabulary record."""
    vocab = vocabulary_service.create(
        system_identity,
        {
            "id": "software",
            "icon": "code",
            "type": "resourcetypes",
            "props": {
                "csl": "software",
                "datacite_general": "Software",
                "datacite_type": "",
                "openaire_resourceType": "0029",
                "openaire_type": "software",
                "eurepo": "info:eu-repo/semantics/other",
                "schema.org": "https://schema.org/SoftwareSourceCode",
                "subtype": "",
                "type": "software",
            },
            "title": {"en": "Software", "de": "Software"},
            "tags": ["depositable", "linkable"],
        },
    )
    Vocabulary.index.refresh()

    return vocab


@pytest.fixture(scope="module")
def swh_service(mock_swh_client):
    """Mocks a SWH service."""
    client = mock_swh_client()
    current_swh_service
    monkeypatch.setattr("invenio_swh.service.SWHService", MagicMock())
    pass


@pytest.fixture(scope="module")
def mock_swh_client():
    def _request(*args, **kwargs):
        response = MagicMock()
        response.status = 200
        content = {}
        return response, content

    mock_client = MagicMock()
    mock_client.h.request = MagicMock(side_effect=_request)

    yield mock_client
