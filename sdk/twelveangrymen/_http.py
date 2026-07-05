"""
Thin transport layer over httpx. Handles auth headers, retrying transient
failures, and mapping HTTP error responses onto the SDK's exception hierarchy.
Kept separate from the resource/model layer so an async transport can be
added later without touching Policy/Rule/Content at all.
"""

import random
import time

import httpx

from . import exceptions as exc


class HTTPTransport:
    def __init__(self, api_key: str, base_url: str, timeout: float = 30.0, max_retries: int = 2):
        self._client = httpx.Client(
            base_url=base_url,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=timeout,
        )
        self.max_retries = max_retries

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "HTTPTransport":
        return self

    def __exit__(self, *exc_info) -> None:
        self.close()

    def request(self, method: str, path: str, **kwargs) -> httpx.Response:
        attempt = 0
        while True:
            try:
                response = self._client.request(method, path, **kwargs)
            except httpx.RequestError as e:
                if attempt >= self.max_retries:
                    raise exc.APIConnectionError(f"Could not reach the Jury API: {e}") from e
                self._sleep_backoff(attempt)
                attempt += 1
                continue

            if response.status_code >= 500 and attempt < self.max_retries:
                self._sleep_backoff(attempt)
                attempt += 1
                continue

            if response.status_code >= 400:
                raise self._map_error(response)

            return response

    @staticmethod
    def _sleep_backoff(attempt: int) -> None:
        # Exponential backoff with jitter. Only used for connection errors and
        # 5xx responses -- 4xx responses are never retried, since retrying a
        # bad request or a duplicate-name conflict just gets the same answer.
        delay = (2 ** attempt) * 0.5 + random.uniform(0, 0.25)
        time.sleep(delay)

    @staticmethod
    def _map_error(response: httpx.Response) -> exc.JuryError:
        try:
            detail = response.json().get("detail", response.text)
        except Exception:
            detail = response.text

        status = response.status_code
        message = f"{status}: {detail}"

        if status == 401:
            return exc.AuthenticationError(message, status, detail)
        if status == 404:
            return exc.NotFoundError(message, status, detail)
        if status == 409:
            return exc.ConflictError(message, status, detail)
        if status == 422:
            return exc.ValidationError(message, status, detail)
        if status == 429:
            if "daily check limit" in str(detail).lower():
                return exc.QuotaExceededError(message, status, detail)
            return exc.RateLimitedError(message, status, detail)
        if status >= 500:
            return exc.ServerError(message, status, detail)
        return exc.JuryError(message, status, detail)