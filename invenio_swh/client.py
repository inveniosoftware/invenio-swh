# -*- coding: utf-8 -*-
#
# Copyright (C) 2023 CERN.
#
# Invenio-SWH is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.
"""Client integration with SWH."""

import json
import urllib

import xmltodict
from lxml import etree

from invenio_swh.errors import ClientException
from invenio_swh.serializer import SoftwareHeritageXMLSerializer


class SWHCLient(object):
    """Abstraction of a client for interacting with SWH."""

    serializer = SoftwareHeritageXMLSerializer

    def __init__(self, client, collection_iri, serializer_cls=None):
        """Initializes the SWH client."""
        self.client = client
        self.serializer = serializer_cls() if serializer_cls else self.serializer()
        self._collection_iri = collection_iri

    @property
    def collection_iri(self):
        """Returns the collection IRI."""
        return self._collection_iri

    def _cleanup_data(self, data: dict, tags: list):
        """
        Cleans up the data dictionary by replacing specified tags.

        Args:
            data (dict): The data dictionary to be cleaned up.
            tags (tuple): A list of tuples tuple of (find, replace) pairs specifying the tags to be replaced.

        Returns:
            dict: The cleaned up data dictionary.
        """
        stringified = json.dumps(data)
        for t in tags:
            assert isinstance(t, tuple)
            find, replace = t
            stringified = stringified.replace(find, replace)
        return json.loads(stringified)

    def edit_media_iri(self, deposit_id):
        """Returns the Edit IRI of a deposit, used for file uploads."""
        suffix = "media"
        return urllib.parse.urljoin(self.collection_iri, f"{deposit_id}/{suffix}/")

    def se_iri(self, deposit_id):
        """Returns the Edit IRI of a deposit, used for metadata updates."""
        suffix = "metadata"
        return urllib.parse.urljoin(self.collection_iri, f"{deposit_id}/{suffix}/")

    def status_iri(self, deposit_id):
        """Returns the status IRI of a deposit."""
        suffix = "status"
        return urllib.parse.urljoin(self.collection_iri, f"{deposit_id}/{suffix}/")

    def create_deposit(self, codemeta_json: dict):
        """Creates a deposit in SWH.

        The codemeta metadata is transformed to XML and then sent to SWH.
        """
        headers = {}
        headers["Content-Type"] = "application/atom+xml;type=entry"
        headers["In-Progress"] = "true"
        swh_compatible_data = self._cleanup_data(
            codemeta_json, [("@type", "type"), ("@id", "id")]
        )
        data = self.serializer.format_serializer.serialize_object(
            {"atom:entry": swh_compatible_data}
        )
        headers["Content-Length"] = str(len(data))
        resp, content = self.client.h.request(
            self.collection_iri, "POST", headers=headers, payload=data
        )
        if resp.status >= 300:
            raise ClientException(f"Failed to create deposit: {resp.status}")
        return self._parse_response(content)

    def update_deposit_files(self, deposit_id, file, file_metadata: dict) -> None:
        """Updates the files of a deposit in SWH.

        File must be a readable buffer.
        """
        headers = {}
        headers["Content-Type"] = str(file_metadata.get("mimetype"))
        headers["Content-MD5"] = str(file_metadata.get("checksum").removeprefix("md5:"))
        headers["Content-Length"] = str(file_metadata.get("size"))
        fname = file_metadata.get("filename")
        headers["Content-Disposition"] = f"attachment; filename={fname}"
        headers["In-Progress"] = "true"
        headers["Packaging"] = "http://purl.org/net/sword/package/SimpleZip"
        resp, content = self.client.h.request(
            self.edit_media_iri(deposit_id),
            "PUT",
            headers=headers,
            payload=file.read(),
        )
        file.close()
        if resp.status >= 300:
            raise ClientException(
                f"Failed to update deposit files {deposit_id}: {resp.status}"
            )
        return self._parse_response(content)

    def complete_deposit(self, deposit_id: int) -> dict:
        """Completes a deposit in SWH."""
        headers = {}
        headers["Content-Type"] = "application/atom+xml;type=entry"
        headers["In-Progress"] = "false"
        headers["Content-Length"] = "0"
        resp, content = self.client.h.request(
            self.se_iri(deposit_id), "POST", headers=headers
        )
        if resp.status >= 300:
            raise ClientException(
                f"Failed to complete deposit {deposit_id}: {resp.status}"
            )
        return self._parse_response(content)

    def get_deposit_status(self, deposit_id: int) -> dict:
        """Returns the status of a deposit."""
        resp, content = self.client.h.request(self.status_iri(deposit_id), "GET")
        return self._parse_response(content)

    def _parse_response(self, response_obj: bytes) -> dict:
        """Parses the response from SWH and returns a dict."""
        if not response_obj or response_obj == b"":
            return {}
        response_str = response_obj.decode("utf-8")
        _etree = self.serializer.format_serializer.to_etree(response_str)
        res_dict = dict(xmltodict.parse(etree.tounicode(_etree)))
        # "entry" is still a ``OrderedDict`` that needs to be casted
        return dict(res_dict["entry"])
