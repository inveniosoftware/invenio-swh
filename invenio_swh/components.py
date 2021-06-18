import logging
import typing
from flask import current_app
from invenio_drafts_resources.records import Draft
from invenio_records import Record
from lxml import etree

from invenio_rdm_records.records import RDMDraft
from invenio_records_resources.services.records.components import (
    ServiceComponent,
)
from invenio_swh import InvenioSWH, tasks
from invenio_swh.enum import ExtDataType
from invenio_swh.exceptions import (
    InvenioSWHException,
    MissingMandatoryMetadataException,
)
from sword2 import Deposit_Receipt

logger = logging.getLogger(__name__)


class InvenioSWHComponent(ServiceComponent):
    """A service component providing SWH integration with records."""

    def __init__(self, service, *, extension_name=InvenioSWH.extension_name):
        super().__init__(service)
        self.extension_name = extension_name

    def create(self, identity, *, data, record, errors):
        logger.debug("Record create (in_progress=%s)", isinstance(record, Draft))
        self.sync_to_swh(data, record, in_progress=isinstance(record, Draft))

    def update(self, identity, *, data, record):
        logger.debug("Record update (in_progress=%s)", isinstance(record, Draft))
        self.sync_to_swh(data, record, in_progress=False)

    def publish(self, identity, *, draft, record):
        logger.debug("Record publish")
        internal_data = self.extension.get_ext_data(record, ExtDataType.Internal)
        if internal_data.get("edit-media-iri"):
            # By the time the task is executed, the record will have been saved.
            cls_name = f"{type(record).__module__}:{type(record).__qualname__}"
            task_kwargs = {
                "extension_name": self.extension_name,
                "cls_name": cls_name,
                "id": draft.pid.pid_value,
            }
            tasks.upload_files.s(**task_kwargs).apply_async(
                # Hard-coded; not great. Would prefer to tie this to session commit
                countdown=5,
                link=tasks.complete_deposit.s(**task_kwargs),
            )

    def read(self, identity, *, record):
        # Hide our internal metadata from the search index and the user
        # self.set_extension_data(record, self.internal_ext_key, None)
        pass

    def update_draft(self, identity, *, data, record: RDMDraft):
        logger.debug("Record update draft")
        self.sync_to_swh(data, record, in_progress=True)

    def sync_to_swh(self, data: dict, record: Record, in_progress: bool):
        user_data = self.extension.get_ext_data(record, ExtDataType.UserFacing)
        internal_data = self.extension.get_ext_data(record, ExtDataType.Internal)

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
            if result.edit:
                internal_data["edit-iri"] = result.edit
            if result.edit_media:
                internal_data["edit-media-iri"] = result.edit_media
            if result.se_iri:
                internal_data["se-iri"] = result.se_iri
            if result.links.get("alternate"):
                internal_data["status-iri"] = result.links["alternate"][0]["href"]

        print(internal_data)

        self.extension.set_ext_data(record, ExtDataType.UserFacing, user_data)
        self.extension.set_ext_data(record, ExtDataType.Internal, internal_data)

    @property
    def extension(self) -> InvenioSWH:
        """Returns the associated invenio-swh extension for this component"""
        return current_app.extensions[self.extension_name]
