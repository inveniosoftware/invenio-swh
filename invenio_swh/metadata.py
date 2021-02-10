from lxml import etree, builder

import sword2
from .exceptions import (
    MissingMandatoryMetadataException,
    NotSoftwareRecordException,
    RecordHasNoFilesException,
)

CodeMeta = builder.ElementMaker(namespace="https://doi.org/10.5063/SCHEMA/CODEMETA-2.0")


class SWHMetadata:
    namespaces = {
        "codemeta": "https://doi.org/10.5063/SCHEMA/CODEMETA-2.0",
        "swh": "https://www.softwareheritage.org/schema/2018/deposit",
    }

    def __init__(self, extension):
        self.extension = extension

    def __call__(self, data: dict) -> sword2.Entry:
        if not self.is_software_record_data(data):
            raise NotSoftwareRecordException

        if data.get("files", {}).get("enabled") is False:
            raise RecordHasNoFilesException(
                "Depositing to Software Heritage requires a non-metadata-only record."
            )

        entry = sword2.Entry()
        for prefix in self.namespaces:
            entry.register_namespace(prefix, self.namespaces[prefix])

        self.add_atom_metadata(entry, data)
        self.add_codemeta_metadata(entry, data)
        self.add_swh_metadata(entry, data)

        return entry

    def add_atom_metadata(self, entry: sword2.Entry, data: dict) -> None:
        try:
            entry.add_field("title", data["metadata"]["title"])
        except KeyError as e:
            raise MissingMandatoryMetadataException("A title is required.") from e

        if not data["metadata"].get("creators"):
            raise MissingMandatoryMetadataException("At least one creator is required.")

        for creator in data["metadata"].get("creators"):
            # TODO: The schema says identifiers are a list of dicts
            orcid_uri = (
                ("https://orcid.org/" + creator["identifiers"]["orcid"])
                if creator.get("identifiers", {}).get("orcid")
                else None
            )
            # TODO: The schema says this should be creator['person_or_org']['name']
            entry.add_author(name=creator["name"], uri=orcid_uri)

    def add_codemeta_metadata(self, entry: sword2.Entry, data: dict) -> None:
        for date in data["metadata"].get("dates", []):
            if not date.get("date"):
                continue
            date_type, date_value = date.get("type"), date["date"]
            if date_type == "created":
                entry.add_field("codemeta_dateCreated", date_value)
            if date_type == "updated":
                entry.add_field("codemeta_datePublished", date_value)

        for rights in data["metadata"].get("rights", []):
            entry.entry.append(
                CodeMeta.license(
                    CodeMeta.name(rights["rights"]),
                    CodeMeta.url(rights["url"]),
                )
            )

    def add_swh_metadata(self, entry: sword2.Entry, data: dict) -> None:
        pass

    def is_software_record_data(self, data: dict) -> bool:
        try:
            return data["metadata"]["resource_type"]["type"] == "software"
        except KeyError:
            return False
