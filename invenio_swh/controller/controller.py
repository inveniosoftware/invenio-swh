# -*- coding: utf-8 -*-
#
# Copyright (C) 2023 CERN.
#
# Invenio-RDM is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.
"""Controller for Software Heritage integration."""

from invenio_swh.client import SWHCLient
from invenio_swh.errors import DeserializeException


class SWHController(object):
    def __init__(self, client: SWHCLient) -> None:
        self.client = client

    def _parse_response(self, data: dict) -> dict:
        if not data:
            return {}

        dpid = data.get("deposit_id")
        if not dpid:
            raise DeserializeException("Failed to deserialize deposit")
        res = {
            "deposit_id": dpid,
            "deposit_status": data.get("deposit_status"),
            "deposit_swhid": data.get("deposit_swh_id"),
            "response": data,
        }
        return res

    def fetch_deposit_status(self, deposit_id: int) -> dict:
        res = self.client.get_deposit_status(deposit_id)
        return self._parse_response(res)

    def create_deposit(self, metadata: dict) -> dict:
        res = self.client.create_deposit(metadata)
        return self._parse_response(res)

    def complete_deposit(self, deposit_id: int) -> dict:
        res = self.client.complete_deposit(deposit_id)
        return self._parse_response(res)

    def update_deposit_files(self, deposit_id: int, files, files_metadata) -> dict:
        res = self.client.update_deposit_files(deposit_id, files, files_metadata)
        return self._parse_response(res)
