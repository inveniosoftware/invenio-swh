# -*- coding: utf-8 -*-
#
# Copyright (C) 2024 CERN
#
# invenio-swh is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
"""Metadata tests for Invenio-SWH."""

# import pytest
# import xmldiff.main
# from lxml import etree

# from invenio_swh import InvenioSWH, exceptions


# def test_not_software_metadata(example_record):
#     ext = InvenioSWH()
#     del example_record["metadata"]["resource_type"]
#     with pytest.raises(exceptions.NotSoftwareRecordException):
#         ext.metadata({})


# def test_metadata_with_missing_title(example_record):
#     ext = InvenioSWH()
#     del example_record["metadata"]["title"]
#     with pytest.raises(exceptions.MissingMandatoryMetadataException):
#         ext.metadata(example_record)


# def test_metadata_with_missing_creators(example_record):
#     ext = InvenioSWH()
#     del example_record["metadata"]["creators"]
#     with pytest.raises(exceptions.MissingMandatoryMetadataException):
#         ext.metadata(example_record)


# def test_metadata_for_example_record(example_record):
#     ext = InvenioSWH()
#     metadata_entry = ext.metadata(example_record)
#     print(etree.tounicode(metadata_entry.entry))
#     assert not xmldiff.main.diff_texts(
#         etree.tounicode(metadata_entry.entry),
#         f"""
#         <entry xmlns="http://www.w3.org/2005/Atom"
#                xmlns:dcterms="http://purl.org/dc/terms/"
#                xmlns:atom="http://www.w3.org/2005/Atom"
#                xmlns:codemeta="https://doi.org/10.5063/SCHEMA/CODEMETA-2.0"
#                xmlns:swh="https://www.softwareheritage.org/schema/2018/deposit">
#             <generator uri="http://bitbucket.org/beno/python-sword2"
#                 version="0.1"/>
#             {etree.tounicode(metadata_entry.entry.xpath(
#                 'atom:updated', namespaces=metadata_entry.nsmap)[0])}
#             <atom:title>Invenio</atom:title>
#             <codemeta:author>
#                 <codemeta:name>CERN</codemeta:name>
#             </codemeta:author>
#             <codemeta:author>
#                 <codemeta:name>other contributors</codemeta:name>
#             </codemeta:author>
#             <codemeta:dateCreated>2019-01-01</codemeta:dateCreated>
#             <codemeta:datePublished>2021-01-25</codemeta:datePublished>
#             <codemeta:license>
#                 <codemeta:name>MIT License</codemeta:name>
#                 <codemeta:url>http://spdx.org/licenses/MIT</codemeta:url>
#             </codemeta:license>
#         </entry>
#     """,
#     )
