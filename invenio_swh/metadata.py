from lxml import etree, builder

import sword2
from .exceptions import (
    MissingMandatoryMetadataException,
    NotSoftwareRecordException,
    RecordHasNoFilesException,
    SoftwareNotOpenlyPublishedException,
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

        if (
            data.get("access", {}).get("record") != "public"
            or data.get("access", {}).get("files") != "public"
        ):
            raise SoftwareNotOpenlyPublishedException(
                "Software Heritage only accepts deposits where both the record and "
                "files are openly published."
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

    def add_codemeta_metadata(self, entry: sword2.Entry, data: dict) -> None:
        if not data["metadata"].get("creators"):
            raise MissingMandatoryMetadataException("At least one creator is required.")

        for key, CodeMeta_element in [
            ("creators", CodeMeta.author),
            ("contributors", CodeMeta.contributor),
        ]:
            for creator in data["metadata"].get(key, []):
                # TODO: The schema says identifiers are a list of dicts
                orcids = [
                    identifier["identifier"]
                    for identifier in creator["person_or_org"].get("identifiers", [])
                    if identifier["scheme"] == "orcid"
                ]
                person = CodeMeta_element(
                    CodeMeta.name(creator["person_or_org"]["name"])
                )
                if orcids:
                    person.append(CodeMeta.id(f"https://orcid.org/{orcids[0]}"))
                for affiliation in creator.get("affiliations", []):
                    person.append(CodeMeta.affiliation(affiliation["name"]))
                entry.entry.append(person)

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
                    CodeMeta.name(rights["title"]),
                    CodeMeta.url(f"http://spdx.org/licenses/{rights['id']}"),
                )
            )

        if data["metadata"].get("description"):
            entry.entry.append(
                # TODO: Not explicitly marked as text/html
                CodeMeta.description(data["metadata"]["description"])
            )

        if data["metadata"].get("version"):
            entry.entry.append(CodeMeta.softwareVersion(data["metadata"]["version"]))

    def add_swh_metadata(self, entry: sword2.Entry, data: dict) -> None:
        pass

    def is_software_record_data(self, data: dict) -> bool:
        try:
            return data["metadata"]["resource_type"]["id"] == "software"
        except KeyError:
            return False
