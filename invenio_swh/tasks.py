import os

import tempfile

import zipfile

from celery.app import shared_task
from flask import current_app
from invenio_records.api import RecordBase
from werkzeug.utils import import_string

from invenio_swh import InvenioSWH


@shared_task
def upload_files(extension_name: str, cls_name: str, id: str) -> None:
    extension = current_app.extensions[extension_name]
    assert isinstance(extension, InvenioSWH)

    cls = import_string(cls_name)
    assert issubclass(cls, RecordBase)
    record = cls.pid.resolve(id, registered_only=False)

    client = extension.sword_client

    with tempfile.TemporaryFile() as f:
        zip = zipfile.ZipFile(f)

        for file in record.bucket.objects:
            with file.open() as g:
                zip.write(file.key, g)

        zip.close()

        f.seek(0)

        client.update_files_for_resource(f, "package.zip")

    print(record)
