import unittest.mock

import pytest
from flask import Flask
from flask_principal import Identity
from invenio_rdm_records.services import RDMRecordService

from invenio_swh import InvenioSWH
from invenio_swh.components import InvenioSWHComponent


def test_create_draft_non_software(
    rdm_with_swh_record_service: RDMRecordService,
    identity_simple: Identity,
    base_app: Flask,
    database,
    location,
):
    with unittest.mock.patch.object(
        InvenioSWH, "sword_client"
    ) as sword_client:
        record_item = rdm_with_swh_record_service.create(
            identity_simple, {}, None
        )
        assert not sword_client.create.called
        with pytest.raises(KeyError):
            _ = record_item._record["ext"][
                InvenioSWHComponent.internal_ext_key
            ]


def test_create_draft_software(
    rdm_with_swh_record_service: RDMRecordService,
    identity_simple: Identity,
    example_record,
    base_app: Flask,
    database,
    location,
):
    with unittest.mock.patch.object(
        InvenioSWH, "sword_client"
    ) as sword_client:
        sword_client.create.return_value.edit = "http://sword.invalid/edit-iri"
        sword_client.create.return_value.edit_media = (
            "http://sword.invalid/edit-media-iri"
        )
        sword_client.create.return_value.se_iri = "http://sword.invalid/se-iri"

        record_item = rdm_with_swh_record_service.create(
            identity_simple, example_record, None
        )
        assert sword_client.create.called

        internal_ext_data = record_item._record["ext"][
            InvenioSWHComponent.internal_ext_key
        ]
