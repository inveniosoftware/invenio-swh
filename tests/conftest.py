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

import pytest
from flask import Flask
from flask_babelex import Babel
from flask_principal import Identity, Need, UserNeed
from flask_sqlalchemy import SQLAlchemy
from invenio_access import InvenioAccess
from invenio_files_rest import InvenioFilesREST
from invenio_jsonschemas import InvenioJSONSchemas
from invenio_rdm_records import InvenioRDMRecords
from invenio_rdm_records.services import RDMRecordService
from invenio_rdm_records.services.config import RDMRecordServiceConfig
from invenio_records import InvenioRecords

from invenio_swh import InvenioSWH
from invenio_swh.components import InvenioSWHComponent
from invenio_swh.views import blueprint


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
            JSONSCHEMAS_HOST="localhost",
            INVENIO_SWH_COLLECTION_IRI="http://swh.invalid/"
        )

        Babel(app)
        SQLAlchemy(app)

        InvenioSWH(app)
        InvenioAccess(app)
        InvenioRecords(app)
        InvenioRDMRecords(app)
        InvenioJSONSchemas(app)
        InvenioFilesREST(app)

        app.register_blueprint(blueprint)

        return app

    return app_factory


@pytest.fixture()
def example_record():
    """An example record as a JSON-like Python structure."""
    with open(
        os.path.join(
            os.path.dirname(__file__), "fixtures", "example-record.json"
        )
    ) as f:
        return json.load(f)


class RDMWithSWHRecordServiceConfig(RDMRecordServiceConfig):
    """A record service config with our SWH component."""

    indexer_cls = unittest.mock.Mock

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
    i.provides.add(Need(method="system_role", value="any_user"))
    return i
