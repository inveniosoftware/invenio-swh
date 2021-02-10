class InvenioSWHException(Exception):
    annotate_record = False
    """Whether to annotate a record when this exception is raised.

    Errors may occur during processing which should be fed back to the user. To support
    this, code that performs actions should set `record['ext']['swh']['error']` to the
    string value of the exception if `annotate_record` is True. If no exceptions occur
    during an operation, this key should be cleared.
    """


class MissingMandatoryMetadataException(InvenioSWHException, ValueError):
    annotate_record = True


class NotSoftwareRecordException(InvenioSWHException, ValueError):
    pass


class RecordHasNoFilesException(InvenioSWHException):
    annotate_record = True
