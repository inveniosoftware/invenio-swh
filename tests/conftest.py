# -*- coding: utf-8 -*-
#
# Copyright (C) 2020-2024 CERN
# Copyright (C) 2020 Cottage Labs LLP.
#
# invenio-swh is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Pytest configuration.

See https://pytest-invenio.readthedocs.io/ for documentation on which test
fixtures are available.
"""
from collections import namedtuple
from io import BytesIO
from unittest.mock import MagicMock, patch
from zipfile import ZipFile

import pytest
from flask_principal import Identity, Need, UserNeed
from invenio_access.permissions import system_identity
from invenio_app.factory import create_api as _create_api
from invenio_rdm_records.proxies import current_rdm_records_service
from invenio_vocabularies.proxies import current_service as vocabulary_service
from invenio_vocabularies.records.api import Vocabulary

from invenio_swh.client import SWHCLient


@pytest.fixture(scope="module")
def zip_file():
    """ZIP fixture."""
    memfile = BytesIO()
    zipfile = ZipFile(memfile, "w")
    zipfile.writestr("test.txt", "hello world")
    zipfile.close()
    memfile.seek(0)
    return memfile


@pytest.fixture(scope="module")
def create_app(instance_path, mock_client):
    """Application factory fixture."""
    with patch("invenio_swh.ext.sword2", mock_client):
        with patch.object(SWHCLient, "_parse_response", lambda x, y: y):
            yield _create_api


@pytest.fixture(scope="module")
def app_config(app_config):
    """Application configuration fixture."""
    app_config["SWH_ENABLED"] = True
    app_config["SWH_USERNAME"] = "test"
    app_config["SWH_PASSWORD"] = "test"
    app_config["JSONSCHEMAS_HOST"] = "not-used"
    app_config["RECORDS_REFRESOLVER_CLS"] = (
        "invenio_records.resolver.InvenioRefResolver"
    )
    app_config["RECORDS_REFRESOLVER_STORE"] = (
        "invenio_jsonschemas.proxies.current_refresolver_store"
    )

    # Needed for files to work
    app_config["FILES_REST_STORAGE_CLASS_LIST"] = {
        "L": "Local",
        "F": "Fetch",
        "R": "Remote",
    }
    app_config["FILES_REST_DEFAULT_STORAGE_CLASS"] = "L"

    return app_config


RunningApp = namedtuple(
    "RunningApp",
    ["app", "location", "cache", "resource_type_v"],
)


@pytest.fixture
def running_app(app, location, cache, resource_type_v):
    """Provide an app with the typically needed db data loaded.

    All of these fixtures are often needed together, so collecting them
    under a semantic umbrella makes sense.
    """
    return RunningApp(app, location, cache, resource_type_v)


@pytest.fixture(scope="function")
def user(UserFixture, app, db):
    """General user for requests."""
    user = UserFixture(email="user1@example.org", password="user1")
    user.create(app, db)

    return user


@pytest.fixture(scope="function")
def minimal_record(running_app):
    """Minimal record data as dict coming from the external world."""
    return {
        "access": {
            "record": "public",
            "files": "public",
        },
        "files": {"enabled": True},  # Most tests don't care about file upload
        "metadata": {
            "publication_date": "2020-06-01",
            "resource_type": {
                "id": "software",
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


def add_file_to_draft(identity, draft_id, file_name, file_contents):
    """Add a file to the draft."""
    draft_file_service = current_rdm_records_service.draft_files

    draft_file_service.init_files(identity, draft_id, data=[{"key": file_name}])
    draft_file_service.set_file_content(identity, draft_id, file_name, file_contents)
    result = draft_file_service.commit_file(identity, draft_id, file_name)
    return result


@pytest.fixture(scope="function")
def create_record_factory(identity_simple, location):
    """Return a factory to create and publish a record with minimal data with, or without, files."""

    def _inner(metadata, files=[]):
        s = current_rdm_records_service
        draft = s.create(identity_simple, metadata)
        if files:
            for fname, fdata in files:
                add_file_to_draft(identity_simple, draft.id, fname, fdata)
        return s.publish(identity_simple, draft.id)

    return _inner


@pytest.fixture(scope="function")
def identity_simple(user):
    """Return simple identity fixture."""
    i = Identity(1)
    i.provides.add(UserNeed(1))
    i.provides.add(Need(method="system_role", value="authenticated_user"))
    i.provides.add(Need(method="system_role", value="any_user"))
    return i


@pytest.fixture(scope="module")
def resource_type_type(app):
    """Resource type vocabulary type."""
    return vocabulary_service.create_type(system_identity, "resourcetypes", "rsrct")


@pytest.fixture(scope="module")
def resource_type_v(app, resource_type_type):
    """Resource type vocabulary record."""
    vocabulary_service.create(
        system_identity,
        {
            "id": "dataset",
            "icon": "table",
            "props": {
                "csl": "dataset",
                "datacite_general": "Dataset",
                "datacite_type": "",
                "openaire_resourceType": "21",
                "openaire_type": "dataset",
                "eurepo": "info:eu-repo/semantics/other",
                "schema.org": "https://schema.org/Dataset",
                "subtype": "",
                "type": "dataset",
            },
            "title": {"en": "Dataset"},
            "tags": ["depositable", "linkable"],
            "type": "resourcetypes",
        },
    )
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
def mock_client():
    """Mock client."""

    def _request(*args, **kwargs):
        assert len(args) >= 2
        response = MagicMock()
        if args[1] == "POST":
            if "/metadata" in args[0]:
                # Deposit completion
                response.status = 200
            else:
                # Deposit creation
                response.status = 201

            content = {
                "deposit_id": 1,
            }
            return response, content
        elif args[1] == "PUT" and "/media" in args[0]:
            # PUT is used for files
            assert all([x in kwargs for x in ("payload", "headers")])
            assert all(
                [
                    x in kwargs["headers"]
                    for x in (
                        "Content-Type",
                        "Content-MD5",
                        "Content-Length",
                        "Content-Disposition",
                        "In-Progress",
                        "Packaging",
                    )
                ]
            )
            response.status = 204
            return response, None
        elif args[1] == "GET" and "/status" in args[0]:
            response.status = 200
            content = {
                "deposit_status": "loading",
                "deposit_id": 1,
                "deposit_swh_id": "swh:1:dir:1",
            }
            return response, content
        else:
            raise Exception("Unkwnown request")

    mock_client = MagicMock()
    mock_client.Connection().h.request.side_effect = _request

    yield mock_client
