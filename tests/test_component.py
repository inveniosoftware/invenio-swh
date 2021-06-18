import unittest.mock
from io import BytesIO

import pytest
from flask import Flask
from flask_principal import Identity
from invenio_rdm_records.records import RDMRecord
from invenio_rdm_records.services import RDMFileDraftServiceConfig, \
    RDMFileRecordServiceConfig, RDMRecordService
from invenio_records_resources.services import FileService

from invenio_swh import InvenioSWH
from invenio_swh.components import InvenioSWHComponent
from invenio_swh.enum import ExtDataType


@pytest.fixture
def mock_deposit_response():
    deposit_response = unittest.mock.Mock()
    deposit_response.edit = "http://sword.invalid/edit-iri"
    deposit_response.edit_media = "http://sword.invalid/edit-media-iri"
    deposit_response.se_iri = "http://sword.invalid/se-iri"
    deposit_response.links = {
        "alternate": [{"href": "http://sword.invalid/status-iri"}]
    }
    return deposit_response


def test_create_draft_non_software(
    rdm_with_swh_record_service: RDMRecordService,
    identity_simple: Identity,
    base_app: Flask,
    database,
    location,
):
    with unittest.mock.patch.object(InvenioSWH, "sword_client") as sword_client:
        record_item = rdm_with_swh_record_service.create(identity_simple, {})
        assert not sword_client.create.called
        with pytest.raises(KeyError):
            _ = record_item._record["ext"][InvenioSWHComponent.internal_ext_key]


def test_create_draft_software(
    rdm_with_swh_record_service: RDMRecordService,
    identity_simple: Identity,
    example_record,
    base_app: Flask,
    database,
    location,
    mock_deposit_response,
    resource_type_software,
):
    with unittest.mock.patch.object(InvenioSWH, "sword_client") as sword_client:
        sword_client.create.return_value = mock_deposit_response

        record_item = rdm_with_swh_record_service.create(
            identity_simple, example_record
        )
        assert sword_client.create.called

        ext_data = record_item._record["ext"][
            InvenioSWHComponent(rdm_with_swh_record_service).extension._ext_data_key(
                ExtDataType.Internal
            )
        ]

        assert ext_data["edit-iri"] == mock_deposit_response.edit
        assert ext_data["edit-media-iri"] == mock_deposit_response.edit_media
        assert ext_data["se-iri"] == mock_deposit_response.se_iri


def test_publish_software(
    rdm_with_swh_record_service: RDMRecordService,
    identity_simple: Identity,
    example_record,
    mock_deposit_response,
    base_app: Flask,
    database,
    location,
    resource_type_software,
    files_service,
):

    with unittest.mock.patch.object(InvenioSWH, "sword_client") as sword_client:
        sword_client.create.return_value = mock_deposit_response

        record_item = rdm_with_swh_record_service.create(
            identity_simple, example_record
        )

        record: RDMRecord = record_item._record

        files_service.init_files(
            id_=record.pid.pid_value,
            identity=identity_simple,
            data=[
                {
                    "key": "data.txt",
                },
            ],
        )

        files_service.set_file_content(
            id_=record.pid.pid_value,
            identity=identity_simple,
            file_key="data.txt",
            stream=BytesIO(b"hello"),
        )

        files_service.commit_file(
            id_=record.pid.pid_value,
            identity=identity_simple,
            file_key="data.txt",
        )

        rdm_with_swh_record_service.publish(
            id_=record.pid.pid_value, identity=identity_simple
        )
