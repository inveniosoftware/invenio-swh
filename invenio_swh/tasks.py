# -*- coding: utf-8 -*-
#
# Copyright (C) 2023 CERN.
#
# Invenio-swh is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.
"""Celery tasks for Invenio / Software Heritage integration."""
from datetime import datetime, timedelta, timezone

from celery.app import shared_task
from flask import current_app
from invenio_access.permissions import system_identity
from invenio_rdm_records.proxies import current_rdm_records_service as record_service
from invenio_records_resources.services.uow import UnitOfWork

from invenio_swh.errors import DepositFailed, DepositWaiting, InvalidRecord
from invenio_swh.models import SWHDepositStatus
from invenio_swh.proxies import current_swh_service as service


@shared_task(max_retries=3)
def process_published_record(pid):
    """Process a published record.

    Attempts to create a deposit using Software Heritage service. The local deposit creation is carried out  in a separate transaction
    in order to store the deposit ID and possible failed status.

    Within a separate, single transaction, it uploads files associated with the record to the deposit and then completes it.

    After the deposit is completed, the function daisy chains another celery task to start polling the deposit status.

    If the record is invalid (e.g. not a software record), the function does not retry.

    Args:
    ----
        pid (str): The record ID.

    """
    try:
        record = record_service.read(system_identity, id_=pid)
        # Create the deposit in a separate transaction. If it fails, no deposit is created locally.
        deposit = service.create(record._record)
    except Exception as exc:
        # If it fails, the deposit was rolled back. We can create it later if the record is valid.
        current_app.logger.exception("Failed to create deposition for archival.")
        if not isinstance(exc, InvalidRecord):
            process_published_record.retry(exc=exc)
        return

    try:
        with UnitOfWork() as uow:
            service.upload_files(deposit.id, record._record.files, uow=uow)
            service.complete(deposit.id, uow=uow)
            uow.commit()
    except Exception as exc:
        current_app.logger.exception("Failed to complete deposit archival.")
        raise

    poll_deposit.delay(str(deposit.id))


@shared_task(
    retry_backoff=60,
    autoretry_for=(DepositWaiting,),
    max_retries=5,
    throws=(DepositWaiting,),
    bind=True,
)
def poll_deposit(self, id_):
    """Poll the status of a deposit.

    ``retry_backoff`` specifices that the time between retries will increase exponentially, starting at, e.g, 60 seconds (60, 120, etc  up until the default of 10 minutes).

    Args:
    ----
        self: The Celery task instance.
        id_ (str): The ID of the deposit to poll.

    Raises:
    ------
        StillWaitingException: If the deposit status is "waiting".

    """
    try:
        deposit = service.read(id_).deposit
        service.sync_status(deposit.id)
    except DepositFailed:
        # If the deposit already failed, we don't need to retry.
        return

    # Manually set status to FAILED on last retry.
    # Celery has a bug where it doesn't raise MaxRetriesExceededError, therefore we need to check retries manually.
    if self.request.retries == 5:
        service.update_status(deposit, SWHDepositStatus.FAILED)
        return

    if deposit.status == SWHDepositStatus.WAITING:
        raise DepositWaiting("Deposit is still waiting")


@shared_task()
def cleanup_depositions():
    """Cleanup old depositions."""
    if not current_app.config.get("SWH_ENABLED"):
        current_app.logger.warning()
        return
    Deposit = service.record_cls.model_cls
    # query for records that are stuck in "waiting" and were created in the previous 24 hours
    res = Deposit.query.filter(
        Deposit.status == SWHDepositStatus.WAITING,
        Deposit.created >= datetime.now(timezone.utc) - timedelta(days=1),
    )

    for deposit in res:
        try:
            service.update_status(deposit, SWHDepositStatus.FAILED)
        except Exception as ex:
            # Avoid failing the whole cleanup task if one deposit fails
            current_app.logger.exception("Failed to cleanup deposit.")
            continue
