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
from invenio_records import Record
from . import config
from .enum import ExtDataType
from .metadata import SWHMetadata


class InvenioSWH(object):
    """invenio-swh extension."""

    extension_name = "invenio-swh"

    url_config_key = "INVENIO_SWH_SERVICE_DOCUMENT"
    collection_name_config_key = "INVENIO_SWH_COLLECTION_NAME"
    collection_iri_config_key = "INVENIO_SWH_COLLECTION_IRI"
    username_config_key = "INVENIO_SWH_USERNAME"
    password_config_key = "INVENIO_SWH_PASSWORD"

    detail_side_bar_template_name = (
        "invenio_swh/records/details/side_bar/invenio_swh.html"
    )

    # This is the mapping from Atom status elements to elements in the user-facing
    # extension data
    status_mapping = {
        "sd:deposit_id": "depositId",
        "sd:deposit_status": "status",
        "sd:deposit_swh_id": "swhidCore",
        "sd:deposit_swh_id_context": "swhid",
        "sd:deposit_status_detail": "statusDetail",
        "sd:deposit_origin_url": "originUrl",
    }

    metadata_cls: typing.Type[SWHMetadata] = SWHMetadata

    def __init__(self, app=None):
        """Extension initialization."""
        if app:
            self.init_app(app)

    def init_app(self, app):
        """Flask application initialization."""
        self.init_config(app)
        app.extensions[self.extension_name] = self

        from invenio_rdm_records.services import RDMRecordServiceConfig
        from .components import InvenioSWHComponent

        # Inject our service component
        if InvenioSWHComponent not in RDMRecordServiceConfig.components:
            RDMRecordServiceConfig.components = [
                *RDMRecordServiceConfig.components,
                InvenioSWHComponent,
            ]

        # Inject our record detail sidebar template
        if (
            "APP_RDM_DETAIL_SIDE_BAR_TEMPLATES" in app.config
            and self.detail_side_bar_template_name
            not in app.config["APP_RDM_DETAIL_SIDE_BAR_TEMPLATES"]
        ):
            app.config["APP_RDM_DETAIL_SIDE_BAR_TEMPLATES"].append(
                self.detail_side_bar_template_name
            )

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
            and current_app.config.get(self.collection_iri_config_key)
            and current_app.config.get(self.username_config_key)
            and current_app.config.get(self.password_config_key)
        )

    @property
    def metadata(self) -> SWHMetadata:
        return self.metadata_cls(self)

    def get_ext_data(self, record: Record, type: ExtDataType) -> dict:
        return record.get("ext", {}).get(self._ext_data_key(type), {})

    def set_ext_data(self, record: Record, type: ExtDataType, extension_data) -> None:
        if extension_data:
            if "ext" not in record:
                record["ext"] = {}
            record["ext"][self._ext_data_key(type)] = extension_data
        elif "ext" in record:
            record["ext"].pop(self._ext_data_key(type), None)
            if not record["ext"]:
                del record["ext"]

    def _ext_data_key(self, type: ExtDataType) -> str:
        return type.value
