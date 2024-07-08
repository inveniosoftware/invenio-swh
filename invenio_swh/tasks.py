# -*- coding: utf-8 -*-
#
# Copyright (C) 2023 CERN.
#
# Invenio-swh is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.
"""Celery tasks for Invenio / Software Heritage integration."""
from celery.app import shared_task
from invenio_access.permissions import system_identity
from invenio_rdm_records.proxies import current_rdm_records_service as record_service
from invenio_records_resources.services.uow import UnitOfWork

from invenio_swh.errors import DepositWaiting, InvalidRecord
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
    record = record_service.read(system_identity, id_=pid)

    try:
        # Create the deposit in a separate transaction to store the deposit ID and possible failed status
        deposit = service.create(record._record)
    except Exception as exc:
        # If it fails, the deposit was rolled back. We can create it later if the record is valid.
        if not isinstance(exc, InvalidRecord):
            process_published_record.retry(exc=exc)
        return

    with UnitOfWork() as uow:
        # TODO if these fails, the deposit should be "FAILED" and not "CREATED" or "WAITING".
        service.upload_files(deposit.id, record._record.files, uow=uow)
        service.complete(deposit.id, uow=uow)

    poll_deposit.delay(str(deposit.id))


@shared_task(
    retry_backoff=60,
    autoretry_for=(DepositWaiting,),
    max_retries=5,
    throws=(DepositWaiting,),
    bind=True
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
    deposit = service.read(id_).deposit
    service.sync_status(deposit.id)
    new_status = deposit.status

    # Manually set status to FAILED on last retry.
    # Celery has a bug where it doesn't raise MaxRetriesExceededError, therefore we need to check retries manually.
    if self.request.retries == 5:
        service.handle_status_update(deposit, SWHDepositStatus.FAILED)
        return

    if new_status == SWHDepositStatus.WAITING:
        raise DepositWaiting("Deposit is still waiting")


# @shared_task()
# def retry_failed_deposits():
#     try:
#         result = service.get_unfinished_deposits()
#         for deposit in result:
#             res = service.fetch_remote_status(deposit)
#             status = res.get("deposit_status")
#             service.update_status(deposit, status)
#             if res.get("deposit_swh_id"):
#                 service.update_swhid(deposit, res.get("deposit_swh_id"))
#     except Exception as exc:
#         current_app.logger.exception(str(exc))
