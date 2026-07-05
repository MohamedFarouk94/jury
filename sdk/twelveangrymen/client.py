import os

from ._http import HTTPTransport
from .exceptions import MissingAPIKeyError
from .resources.policies import PoliciesResource

DEFAULT_BASE_URL = "https://mfarouk-jury-backend.hf.space/api"


class Jury:
    """
    Entry point for the Jury SDK.

        import twelveangrymen as jury

        client = jury.Jury(api_key="jk_...")
        policy = client.policies.get("Community Guidelines")
        verdict = policy.evaluate("some user-submitted text")

    Or as a context manager, to close the underlying connection pool cleanly:

        with jury.Jury() as client:
            ...

    Reads JURY_API_KEY / JURY_BASE_URL from the environment if not passed
    explicitly. API keys are managed exclusively via the Jury dashboard --
    this SDK only ever authenticates with one, it doesn't create or revoke them.
    """

    def __init__(self, api_key: str = None, base_url: str = None,
                 timeout: float = 30.0, max_retries: int = 2):
        api_key = api_key or os.getenv("JURY_API_KEY")
        if not api_key:
            raise MissingAPIKeyError(
                "No API key provided. Pass api_key=... or set the JURY_API_KEY "
                "environment variable. Create a key from the Jury dashboard."
            )

        base_url = base_url or os.getenv("JURY_BASE_URL", DEFAULT_BASE_URL)

        self._transport = HTTPTransport(api_key, base_url, timeout=timeout, max_retries=max_retries)
        self.policies = PoliciesResource(self._transport)

    def close(self) -> None:
        self._transport.close()

    def __enter__(self) -> "Jury":
        return self

    def __exit__(self, *exc_info) -> None:
        self.close()