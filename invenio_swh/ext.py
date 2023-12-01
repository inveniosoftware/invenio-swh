# -*- coding: utf-8 -*-
#
# Copyright (C) 2020 CERN
# Copyright (C) 2020 Cottage Labs LLP.
#
# invenio-swh is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Support for onward deposit of software artifacts to Software Heritage."""

import sword2
from flask.blueprints import Blueprint
from invenio_rdm_records.services.signals import post_publish_signal

from invenio_swh.client import SWHCLient
from invenio_swh.controller import SWHController
from invenio_swh.service import SWHService
from invenio_swh.signals import post_publish_receiver

from . import config

blueprint = Blueprint(
    "invenio_swh",
    __name__,
    template_folder="templates",
)


class InvenioSWH(object):
    """invenio-swh extension."""

    def __init__(self, app=None):
        """Extension initialization."""
        if app:
            self.init_app(app)

    def init_app(self, app):
        """Flask application initialization.

        The extension is only registered if it is enabled and configured.
        """
        self.init_config(app)
        if self.is_enabled(app) and self.is_configured(app):
            self.init_signals()
            self.init_service(app)
            app.extensions["invenio-swh"] = self
            app.register_blueprint(blueprint)

    def init_service(self, app):
        """Initialize the service.

        Both the swh controller and client are injected into the service.
        """
        sword_client = sword2.Connection(
            service_document_iri=app.config["SWH_SERVICE_DOCUMENT"],
            user_name=app.config["SWH_USERNAME"],
            user_pass=app.config["SWH_PASSWORD"],
        )
        client = SWHCLient(sword_client, app.config["SWH_COLLECTION_IRI"])
        controller = SWHController(client)
        self.service = SWHService(controller)

    def init_signals(self):
        """Initialize signals."""
        post_publish_signal.connect(post_publish_receiver)

    def init_config(self, app):
        """Initialize configuration."""
        for k in dir(config):
            if k.startswith("SWH_"):
                app.config.setdefault(k, getattr(config, k))

    def is_enabled(self, app):
        """Return True whether the extension is enabled."""
        return app.config.get("SWH_ENABLED")

    def is_configured(self, app) -> bool:
        """Return whther the extension is properly configured."""
        return bool(
            app.config.get("SWH_SERVICE_DOCUMENT")
            and app.config.get("SWH_USERNAME")
            and app.config.get("SWH_PASSWORD")
            and app.config.get("SWH_ACCEPTED_EXTENSIONS")
            and app.config.get("SWH_ACCEPTED_RECORD_TYPES")
        )
