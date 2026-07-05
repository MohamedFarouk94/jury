"""
Jury Python SDK.

    import twelveangrymen as jury

    client = jury.Jury(api_key="jk_...")
    policy = client.policies.get("Community Guidelines")
    verdict = policy.evaluate("some text")
    verdict.summary()
"""

from .client import Jury
from .models import Policy, Rule
from .verdict import Content, Verdict
from .exceptions import (
    JuryError,
    MissingAPIKeyError,
    APIConnectionError,
    AuthenticationError,
    NotFoundError,
    ResourceGoneError,
    DeletedResourceError,
    StaleReferenceError,
    ConflictError,
    ValidationError,
    QuotaExceededError,
    RateLimitedError,
    ServerError,
    EvaluationTimeoutError,
    UncommittedChangesError,
    CommitError,
    PartialCommitError,
    RuleDoesNotExistError,
)

__version__ = "0.2.0"

__all__ = [
    "Jury",
    "Policy",
    "Rule",
    "Content",
    "Verdict",
    "JuryError",
    "MissingAPIKeyError",
    "APIConnectionError",
    "AuthenticationError",
    "NotFoundError",
    "ResourceGoneError",
    "DeletedResourceError",
    "StaleReferenceError",
    "ConflictError",
    "ValidationError",
    "QuotaExceededError",
    "RateLimitedError",
    "ServerError",
    "EvaluationTimeoutError",
    "UncommittedChangesError",
    "CommitError",
    "PartialCommitError",
    "RuleDoesNotExistError",
]