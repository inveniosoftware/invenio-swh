import lxml.etree
import tarfile
import logging
import tempfile

from celery.app import shared_task
from flask import current_app
from invenio_db import db

from invenio_records.api import RecordBase
from werkzeug.utils import import_string

from invenio_swh import exceptions, InvenioSWH
from invenio_swh.constants import NAMESPACES
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


# Each of these takes a positional-only result parameter that is ignored. This means
# that tasks can be chained together, as we can discard the result passed as the first
# argument to the next task.


@shared_task
def upload_files(
    result=None, /, *, extension_name: str, cls_name: str, id: str
) -> None:
    record = _get_record(cls_name, id)
    extension = _get_extension(extension_name)
    client = extension.sword_client

    internal_data = extension.get_ext_data(record, ExtDataType.Internal)
    if "edit-media-iri" not in internal_data:
        raise exceptions.DepositNotStartedException

    with tempfile.TemporaryFile() as f:
        tar = tarfile.open(fileobj=f, mode="w:gz")

        for object_version in record.bucket.objects:
            with object_version.file.storage().open() as g:
                tarinfo = tarfile.TarInfo(object_version.key)
                tarinfo.size = object_version.file.size
                tar.addfile(tarinfo, fileobj=g)

        tar.close()

        f.seek(0)

        result = client.update_files_for_resource(
            f,
            "package.tar.gz",
            edit_media_iri=internal_data["edit-media-iri"],
            mimetype="application/x-tar",  # Even though it's also gzipped.
            packaging="http://purl.org/net/sword/package/SimpleZip",
            in_progress=True,
        )

        print(result)


@shared_task
def complete_deposit(
    result=None, /, *, extension_name: str, cls_name: str, id: str
) -> None:
    record = _get_record(cls_name, id)
    extension = _get_extension(extension_name)
    client = extension.sword_client

    internal_data = extension.get_ext_data(record, ExtDataType.Internal)
    if "edit-media-iri" not in internal_data:
        raise exceptions.DepositNotStartedException

    client.complete_deposit(se_iri=internal_data["se-iri"])

    # Start looking for the deposit to be processed
    update_status_from_swh.delay(
        extension_name=extension_name, cls_name=cls_name, id=id
    )


@shared_task(
    autoretry_for=(exceptions.DepositNotYetDone,),
    retry_backoff=10,
    retry_kwargs={"max_retries": 20},
)
def update_status_from_swh(
    result=None, /, *, extension_name: str, cls_name: str, id: str
) -> None:
    record = _get_record(cls_name, id)
    extension = _get_extension(extension_name)
    client = extension.sword_client

    internal_data = extension.get_ext_data(record, ExtDataType.Internal)
    if "status-iri" not in internal_data:
        raise exceptions.DepositNotStartedException

    resp, content = client.h.request(internal_data["status-iri"], "GET")
    atom_status = lxml.etree.fromstring(content)

    user_facing_data = extension.get_ext_data(record, ExtDataType.UserFacing)

    for name, key in extension.status_mapping.items():
        elements = atom_status.xpath(f"//{name}", namespaces=NAMESPACES)
        if elements and elements[0].text:
            user_facing_data[key] = elements[0].text

    extension.set_ext_data(record, ExtDataType.UserFacing, user_facing_data)
    record.commit()
    db.session.commit()

    if user_facing_data.get("status") == "error":
        raise exceptions.DepositProcessingFailedException(
            user_facing_data.get("statusDetail")
        )

    if user_facing_data.get("status") != "done":
        raise exceptions.DepositNotYetDone

    print(atom_status)
