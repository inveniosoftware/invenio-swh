# -*- coding: utf-8 -*-
#
# Copyright (C) 2023 CERN.
#
# Invenio-RDM is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.
"""Test swh service module."""

import pytest

from invenio_swh.errors import InvalidRecord
from invenio_swh.models import SWHDepositModel, SWHDepositStatus
from invenio_swh.proxies import current_swh_service as service


def test_deposit_simple_flow(app, minimal_record, zip_file, create_record_factory):
    """Test the entire flow of a swh deposit creation plus completion.

    The swh client is mocked for tests, therefore the responses are mocked to be a success.
    The purpose of this test is to check that the flow of the deposit is correct for success scenarios.
    """
    record = create_record_factory(minimal_record, files=[("test.zip", zip_file)])
    swh_deposit = service.create(record._record)
    assert swh_deposit.status == SWHDepositStatus.CREATED
    assert swh_deposit.model.object_uuid == record._record.id
    assert swh_deposit.id is not None

    service.upload_files(swh_deposit.id, record._record.files)
    # Files are uploaded, but the deposit is not completed yet
    assert swh_deposit.status == SWHDepositStatus.CREATED

    service.complete(swh_deposit.id)
    assert swh_deposit.status == SWHDepositStatus.WAITING

    # After some time, the deposit will be complete (in success scenario)
    service.sync_status(swh_deposit.id)
    assert swh_deposit.status == SWHDepositStatus.SUCCESS
    assert swh_deposit.swhid is not None


def test_deposit_creation_failure(app, minimal_record, zip_file, create_record_factory):
    """Test the creation of a swh deposit (locally)."""
    assert SWHDepositModel.query.count() == 0
    # A record with multiple files should fail and no deposit created locally
    with pytest.raises(InvalidRecord):
        record = create_record_factory(
            minimal_record, files=[("test.zip", zip_file), ("test_two.zip", zip_file)]
        )
        service.create(record._record)

    # A record with no files should fail
    with pytest.raises(InvalidRecord):
        minimal_record["files"] = {"enabled": False}
        record = create_record_factory(minimal_record, files=[])
        service.create(record._record)

    # A record that is not software should fail
    with pytest.raises(InvalidRecord):
        minimal_record["metadata"]["resource_type"]["id"] = "dataset"
        record = create_record_factory(minimal_record, files=[])
        service.create(record._record)

    # A record that is not completely open should be rejected
    with pytest.raises(InvalidRecord):
        minimal_record["access"]["record"] = "restricted"
        record = create_record_factory(minimal_record, files=[])
        service.create(record._record)

    # No deposit should have been created
    assert SWHDepositModel.query.count() == 0


def test_upload_files_failure(
    app, minimal_record, zip_file, create_record_factory, monkeypatch
):
    """Test a scenario where the upload of files fails."""

    def _raise(*args, **kwargs):
        raise Exception("Failed to upload files")

    record = create_record_factory(minimal_record, files=[("test.zip", zip_file)])
    swh_deposit = service.create(record._record)
    assert swh_deposit.status == SWHDepositStatus.CREATED

    # Simulate the controller failed to deposit the files
    monkeypatch.setattr(
        "invenio_swh.controller.SWHController.update_deposit_files",
        lambda x: _raise(),
    )

    service.upload_files(swh_deposit.id, record._record.files)
    assert swh_deposit.status == SWHDepositStatus.FAILED
    assert swh_deposit.id is not None


def test_deposit_completion_failure(
    app, minimal_record, zip_file, create_record_factory, monkeypatch
):
    """Test a scenario where the completion of a deposit fails.

    (e.g. unexpected error from Software Heritage).
    """

    def _raise(*args, **kwargs):
        raise Exception("Failed to complete deposit")

    # Create a deposit
    record = create_record_factory(minimal_record, files=[("test.zip", zip_file)])
    swh_deposit = service.create(record._record)
    assert swh_deposit.status == SWHDepositStatus.CREATED

    # Simulate the controller failed to complete the deposit
    monkeypatch.setattr(
        "invenio_swh.controller.SWHController.complete_deposit",
        lambda x: _raise(),
    )

    # Upload files
    service.upload_files(swh_deposit.id, record._record.files)
    assert swh_deposit.status == SWHDepositStatus.CREATED
    assert swh_deposit.id is not None

    # Complete the deposition
    service.complete(swh_deposit.id)
    assert swh_deposit.status == SWHDepositStatus.FAILED
    assert swh_deposit.swhid is None
