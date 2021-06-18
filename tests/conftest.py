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

import json
import os
import unittest.mock
import uuid

import pytest
from flask import Flask
from flask_babelex import Babel
from flask_principal import Identity, Need, UserNeed
from flask_sqlalchemy import SQLAlchemy
from invenio_access import InvenioAccess
from invenio_access.permissions import system_process
from invenio_files_rest import InvenioFilesREST
from invenio_jsonschemas import InvenioJSONSchemas
from invenio_records_resources import InvenioRecordsResources
from invenio_records_resources.registry import ServiceRegistry
from invenio_records_resources.services import FileService
from invenio_search import InvenioSearch
# from invenio_app.factory import create_app as _create_app

from invenio_rdm_records import InvenioRDMRecords
from invenio_rdm_records.services import RDMRecordService
from invenio_rdm_records.services.config import RDMFileDraftServiceConfig, \
    RDMRecordServiceConfig
from invenio_records import InvenioRecords

from invenio_vocabularies import InvenioVocabularies
from invenio_vocabularies.proxies import current_service as vocabulary_service

from invenio_swh import InvenioSWH
from invenio_swh.components import InvenioSWHComponent
from invenio_swh.views import blueprint

# the primary requirement for the system user's ID is to be unique
# the IDs of users provided by Invenio-Accounts are positive integers
# the ID of an AnonymousIdentity from Flask-Principle is None
# and the documentation for Flask-Principal makes use of strings for some IDs
system_user_id = "system"
"""The user ID of the system itself, used in its Identity."""

system_identity = Identity(system_user_id)
"""Identity used by system processes."""

system_identity.provides.add(system_process)


@pytest.fixture(scope="module")
def celery_config():
    """Override pytest-invenio fixture.

    TODO: Remove this fixture if you add Celery support.
    """
    return {}


@pytest.fixture(scope="module")
def create_app(instance_path, entry_points):
    """Application factory fixture."""

    def app_factory(**config):
        app = Flask("testapp", instance_path=instance_path)

        app.config.update(
            **config,
            # SQLALCHEMY_DATABASE_URI=os.environ.get(
            #     'SQLALCHEMY_DATABASE_URI', 'sqlite:///' + db_filename),
            # TESTING=True,
            JSONSCHEMAS_ENDPOINT="/schemas/",
            INVENIO_SWH_COLLECTION_IRI="http://swh.invalid/"
        )

        Babel(app)
        SQLAlchemy(app)

        InvenioSWH(app)
        InvenioAccess(app)
        InvenioRecords(app)
        InvenioRecordsResources(app)
        InvenioRDMRecords(app)
        InvenioJSONSchemas(app)
        InvenioFilesREST(app)
        InvenioSearch(app)
        InvenioVocabularies(app)

        app.register_blueprint(blueprint)

        return app

    return app_factory


@pytest.fixture(scope='module')
def app_config(app_config):
    app_config['RECORDS_REFRESOLVER_CLS'] = \
        "invenio_records.resolver.InvenioRefResolver"
    app_config['RECORDS_REFRESOLVER_STORE'] = \
        "invenio_jsonschemas.proxies.current_refresolver_store"
    # Variable not used. We set it to silent warnings
    app_config['JSONSCHEMAS_HOST'] = 'not-used'
    return app_config


@pytest.fixture()
def example_record():
    """An example record as a JSON-like Python structure."""
    with open(
        os.path.join(os.path.dirname(__file__), "fixtures", "example-record.json")
    ) as f:
        return json.load(f)


class RDMWithSWHRecordServiceConfig(RDMRecordServiceConfig):
    """A record service config with our SWH component."""

    indexer_cls = unittest.mock.Mock

    components = RDMRecordServiceConfig.components
    if InvenioSWHComponent not in components:
        components = [
            *RDMRecordServiceConfig.components,
            InvenioSWHComponent,
        ]


@pytest.fixture
def rdm_with_swh_record_service():
    """Return a record service with an SWH component plugged in."""
    return RDMRecordService(config=RDMWithSWHRecordServiceConfig)


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
    return vocabulary_service.create_type(
        system_identity, "resource_types", "rsrct")


@pytest.fixture(scope="module")
def resource_type_software(app, resource_type_type):
    """Resource type vocabulary record."""
    return vocabulary_service.create(system_identity, {
        "id": "software",
        "props": {
            "csl": "graphic",
            "datacite_general": "Image",
            "datacite_type": "Photo",
            "openaire_resourceType": "25",
            "openaire_type": "dataset",
            "schema.org": "https://schema.org/Photograph",
            "subtype": "image-photo",
            "subtype_name": "Photo",
            "type": "image",
            "type_icon": "chart bar outline",
            "type_name": "Image",
        },
        "title": {
            "en": "Software"
        },
        "type": "resource_types"
    })


@pytest.yield_fixture()
def files_service(app):
    files_service = FileService(RDMFileDraftServiceConfig)
    registry: ServiceRegistry = app.extensions["invenio-records-resources"].registry
    # Let's pick a random service_id…
    registry.register(files_service, str(uuid.uuid4()))
    try:
        yield files_service
    finally:
        del registry._services[registry.get_service_id(files_service)]
