class InvenioSWHException(Exception):
    annotate_record = False
    """Whether to annotate a record when this exception is raised.

    Errors may occur during processing which should be fed back to the user. To support
    this, code that performs actions should set `record['ext']['swh']['error']` to the
    string value of the exception if `annotate_record` is True. If no exceptions occur
    during an operation, this key should be cleared.
    """


class InvalidRecord(InvenioSWHException):
    """Triggered when the record is not valid to be sent to Software Heritage.

    Examples of an invalid record: record is not fully open (files + metadata).
    """


class ClientException(Exception):
    """Generic implementation of a client exception (e.g. request failed on remote)."""


class DepositWaiting(InvenioSWHException):
    """Raised when the deposit status is "waiting"."""


class DepositFailed(InvenioSWHException):
    """Raised when the deposit status is "failed"."""


####
# Controller exceptions
####
class ControllerException(InvenioSWHException):
    """Generic implementation of a controller exception (e.g. request failed on remote)."""


class DeserializeException(ControllerException):
    """Raised when a remote response failed to be deserialized."""
