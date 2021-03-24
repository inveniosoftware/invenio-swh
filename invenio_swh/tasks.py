import tarfile
import logging
import tempfile

from celery.app import shared_task
from flask import current_app
from invenio_records.api import RecordBase
from werkzeug.utils import import_string

from invenio_swh import exceptions, InvenioSWH
from invenio_swh.enum import ExtDataType

logger = logging.getLogger(__name__)


def _get_record(cls_name: str, id: str) -> RecordBase:
    cls = import_string(cls_name)
    assert issubclass(cls, RecordBase)
    return cls.pid.resolve(id, registered_only=False)


def _get_extension(extension_name: str) -> InvenioSWH:
    extension = current_app.extensions[extension_name]
    assert isinstance(extension, InvenioSWH)
    return extension


@shared_task
def upload_files(extension_name: str, cls_name: str, id: str) -> None:
    record = _get_record(cls_name, id)
    extension = _get_extension(extension_name)
    client = extension.sword_client

    internal_data = extension.get_ext_data(record, ExtDataType.Internal)
    if 'edit-media-iri' not in internal_data:
        raise exceptions.DepositNotStartedException

    with tempfile.TemporaryFile() as f:
        tar = tarfile.open(fileobj=f, mode='w:gz')

        for object_version in record.bucket.objects:
            with object_version.file.storage().open() as g:
                tar.addfile(tarfile.TarInfo(object_version.key), fileobj=g)

        tar.close()

        f.seek(0)

        client.update_files_for_resource(
            f,
            "package.tar.gz",
            edit_media_iri=internal_data['edit-media-iri'],
            mimetype='application/x-tar',  # Even though it's also gzipped.
            packaging='http://purl.org/net/sword/package/SimpleZip',
            in_progress=True,
        )


@shared_task
def complete_deposit(extension_name: str, cls_name: str, id: str) -> None:
    record = _get_record(cls_name, id)
    extension = _get_extension(extension_name)
    client = extension.sword_client

    internal_data = extension.get_ext_data(record, ExtDataType.Internal)
    if 'edit-media-iri' not in internal_data:
        raise exceptions.DepositNotStartedException

    client.complete_deposit(se_iri=internal_data["se-iri"])
