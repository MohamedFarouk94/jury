"""
Exception hierarchy for the Jury SDK.

    JuryError
    ├── MissingAPIKeyError
    ├── APIConnectionError
    ├── AuthenticationError        (401)
    ├── NotFoundError              (404 -- a fresh lookup found nothing)
    ├── ResourceGoneError          ("this used to exist")
    │   ├── DeletedResourceError   (you deleted it yourself; purely local, no network call)
    │   └── StaleReferenceError    (the server told you it's gone, unexpectedly)
    ├── ConflictError              (409 -- duplicate name)
    ├── ValidationError            (422)
    ├── QuotaExceededError         (429 -- daily check limit)
    ├── RateLimitedError           (429 -- login lockout / generic throttling)
    ├── ServerError                (5xx)
    ├── EvaluationTimeoutError     (evaluate()'s internal polling gave up)
    ├── UncommittedChangesError    (tried to evaluate/refresh over staged changes)
    ├── CommitError
    │   └── PartialCommitError     (some staged changes committed, some didn't)
    └── RuleDoesNotExistError      (index- or name-based rule lookup found nothing)

StaleReferenceError inherits from both ResourceGoneError and NotFoundError, so
`except NotFoundError` still catches it, while callers who want to distinguish
"never existed" from "existed and vanished" can catch it specifically.
"""


class JuryError(Exception):
    """Base class for all errors raised by this SDK."""

    def __init__(self, message, status_code=None, detail=None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.detail = detail


class MissingAPIKeyError(JuryError):
    pass


class APIConnectionError(JuryError):
    pass


class AuthenticationError(JuryError):
    pass


class NotFoundError(JuryError):
    pass


class ResourceGoneError(JuryError):
    pass


class DeletedResourceError(ResourceGoneError):
    pass


class StaleReferenceError(ResourceGoneError, NotFoundError):
    pass


class ConflictError(JuryError):
    pass


class ValidationError(JuryError):
    pass


class QuotaExceededError(JuryError):
    pass


class RateLimitedError(JuryError):
    pass


class ServerError(JuryError):
    pass


class EvaluationTimeoutError(JuryError):
    def __init__(self, message, content_id=None):
        super().__init__(message)
        self.content_id = content_id


class UncommittedChangesError(JuryError):
    def __init__(self, message, pending_changes=None):
        super().__init__(message)
        self.pending_changes = pending_changes or {}


class CommitError(JuryError):
    pass


class PartialCommitError(CommitError):
    def __init__(self, message, succeeded=None, failed=None):
        super().__init__(message)
        self.succeeded = succeeded or []  # list of (op, rule_name)
        self.failed = failed or []        # list of (op, rule_name, exception)


class RuleDoesNotExistError(NotFoundError):
    pass