# -*- coding: utf-8 -*-
#
# Copyright (C) 2020 CERN
# Copyright (C) 2020 Cottage Labs LLP.
#
# invenio-swh is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Support for onward deposit of software artifacts to Software Heritage"""

import typing
from flask import current_app

import sword2
from . import config
from .metadata import SWHMetadata


class InvenioSWH(object):
    """invenio-swh extension."""

    extension_name = "invenio-swh"

    url_config_key = "INVENIO_SWH_SERVICE_DOCUMENT"
    collection_name_config_key = "INVENIO_SWH_COLLECTION_NAME"
    collection_iri_config_key = "INVENIO_SWH_COLLECTION_IRI"
    username_config_key = "INVENIO_SWH_USERNAME"
    password_config_key = "INVENIO_SWH_PASSWORD"

    metadata_cls: typing.Type[SWHMetadata] = SWHMetadata

    def __init__(self, app=None):
        """Extension initialization."""
        if app:
            self.init_app(app)

    def init_app(self, app):
        """Flask application initialization."""
        self.init_config(app)
        app.extensions[self.extension_name] = self

    def init_config(self, app):
        """Initialize configuration."""
        # Use theme's base template if theme is installed
        if "BASE_TEMPLATE" in app.config:
            app.config.setdefault(
                "INVENIO_SWH_BASE_TEMPLATE",
                app.config["BASE_TEMPLATE"],
            )
        for k in dir(config):
            if k.startswith("INVENIO_SWH_"):
                app.config.setdefault(k, getattr(config, k))

    @property
    def sword_client(self) -> sword2.Connection:
        if self.is_configured:
            return sword2.Connection(
                service_document_iri=current_app.config[self.url_config_key],
                user_name=current_app.config[self.username_config_key],
                user_pass=current_app.config[self.password_config_key],
            )

    @property
    def collection_name(self) -> str:
        return current_app.config[self.collection_name_config_key]

    @property
    def collection_iri(self) -> str:
        return current_app.config[self.collection_iri_config_key]

    @property
    def is_configured(self) -> bool:
        return bool(
            current_app.config.get(self.url_config_key)
            and current_app.config.get(self.collection_name_config_key)
            and current_app.config.get(self.username_config_key)
            and current_app.config.get(self.password_config_key)
        )

    @property
    def metadata(self) -> SWHMetadata:
        return self.metadata_cls(self)
