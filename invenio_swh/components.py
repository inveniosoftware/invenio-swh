import logging
import typing
from flask import current_app
from invenio_drafts_resources.records import Draft
from invenio_records import Record
from lxml import etree

from invenio_rdm_records.records import BibliographicRecord
from invenio_records_resources.services.records.components import ServiceComponent
from invenio_swh import InvenioSWH
from invenio_swh.exceptions import (
    InvenioSWHException,
    MissingMandatoryMetadataException,
)
from sword2 import Deposit_Receipt

logger = logging.getLogger(__name__)

logging.basicConfig(level=logging.DEBUG)


class InvenioSWHComponent(ServiceComponent):
    """A service component providing SWH integration with records."""

    user_ext_key = "swh"
    internal_ext_key = "swh-internal"

    def __init__(self, service, *, extension_name="invenio-swh"):
        super().__init__(service)
        self.extension_name = extension_name

    def create(self, identity, *, data, record):
        logger.debug("Record create (in_progress=%s)", isinstance(record, Draft))
        self.sync_to_swh(data, record, in_progress=isinstance(record, Draft))

    def update(self, identity, *, data, record):
        logger.debug("Record update (in_progress=%s)", isinstance(record, Draft))
        self.sync_to_swh(data, record, in_progress=False)

    def publish(self, *, draft, record):
        logger.debug("Record publish")
        internal_data = self.get_extension_data(record, self.internal_ext_key)
        if internal_data.get("se-iri"):
            client = self.extension.sword_client
            client.complete_deposit(se_iri=internal_data["se-iri"])

    def read(self, identity, *, record):
        # Hide our internal metadata from the search index and the user
        # self.set_extension_data(record, self.internal_ext_key, None)
        pass

    def update_draft(self, identity, *, data, record: BibliographicRecord):
        logger.debug("Record update draft")
        self.sync_to_swh(data, record, in_progress=True)

    def sync_to_swh(self, data: dict, record: Record, in_progress: bool):
        user_data = self.get_extension_data(record, self.user_ext_key)
        internal_data = self.get_extension_data(record, self.internal_ext_key)

        # Clear any error information
        user_data.pop("error", None)

        try:
            metadata_entry = self.extension.metadata(data)
            logger.info(
                "Extracted metadata for deposit: %s",
                etree.tounicode(metadata_entry.entry),
            )
        except InvenioSWHException as e:
            if e.annotate_record:
                user_data["error"] = str(e)
            logger.debug("Not extracting metadata for SWH deposit", exc_info=e)
            metadata_entry = None

        client = self.extension.sword_client

        result: typing.Optional[Deposit_Receipt]

        if internal_data.get("edit-iri") and metadata_entry:
            result = client.update(
                edit_iri=internal_data["edit-iri"],
                in_progress=in_progress,
                metadata_entry=self.extension.metadata(data),
            )
        elif metadata_entry:
            result = client.create(
                col_iri=self.extension.collection_iri,
                in_progress=in_progress,
                metadata_entry=self.extension.metadata(data),
            )
        else:
            result = None

        if result:
            internal_data.update(
                {
                    "edit-iri": result.edit,
                    "edit-media-iri": result.edit_media,
                    "se-iri": result.se_iri,
                }
            )

        self.set_extension_data(record, self.internal_ext_key, user_data)
        self.set_extension_data(record, self.internal_ext_key, internal_data)

    def get_extension_data(self, record: Record, key: str) -> dict:
        return record.get("ext", {}).get(key, {})

    def set_extension_data(self, record: Record, key: str, extension_data) -> dict:
        if extension_data:
            if "ext" not in record:
                record["ext"] = {}
            record["ext"][key] = extension_data
        elif "ext" in record:
            record["ext"].pop(str, None)
            if not record["ext"]:
                del record["ext"]

    @property
    def extension(self) -> InvenioSWH:
        """Returns the associated invenio-swh extension for this component"""
        return current_app.extensions[self.extension_name]
