"""
Content and Verdict.

Content is a thin, mutable handle on a moderation submission -- it doesn't
need lifecycle staging the way Policy/Rule do, since content is never edited,
only created and polled. Verdict is a Pydantic model: a pure data result with
formatting behavior (summary(), dict(), json()) layered on top.
"""

import time
from typing import Any, Dict, Optional

from pydantic import BaseModel

from . import exceptions as exc


class Content:
    def __init__(self, id, text, policy_id, verdict, created_at, transport, policy=None):
        self.id = id
        self.text = text
        self.policy_id = policy_id
        self.verdict_data = verdict  # raw dict from the API, or None while pending
        self.created_at = created_at
        self._transport = transport
        self._policy = policy

    @classmethod
    def _from_api(cls, data, transport, policy=None):
        return cls(
            id=data["id"], text=data["text"], policy_id=data["policy_id"],
            verdict=data.get("verdict"), created_at=data["created_at"],
            transport=transport, policy=policy,
        )

    def __repr__(self):
        state = "resolved" if self.is_resolved else ("failed" if self.failed else "pending")
        return f"<Content id={self.id!r} state={state}>"

    @property
    def is_resolved(self) -> bool:
        return isinstance(self.verdict_data, dict) and "error" not in self.verdict_data

    @property
    def failed(self) -> bool:
        return isinstance(self.verdict_data, dict) and "error" in self.verdict_data

    def refresh(self) -> "Content":
        """Re-fetch this content's current verdict state from the server."""
        resp = self._transport.request("GET", f"/contents/{self.id}")
        self.verdict_data = resp.json().get("verdict")
        return self

    def wait(self, timeout: float = 30.0, poll_interval: float = 0.5) -> "Verdict":
        """Poll until the verdict resolves, then return it. Raises on timeout or chain failure."""
        deadline = time.monotonic() + timeout
        while True:
            self.refresh()
            if self.verdict_data is not None:
                if self.failed:
                    raise exc.ServerError(
                        f"Moderation failed for content #{self.id}: "
                        f"{self.verdict_data.get('details', self.verdict_data.get('error'))}"
                    )
                return Verdict._from_content(self)

            if time.monotonic() >= deadline:
                raise exc.EvaluationTimeoutError(
                    f"Verdict for content #{self.id} did not resolve within {timeout}s. "
                    f"Call .refresh() or .wait() again later to keep checking.",
                    content_id=self.id,
                )
            time.sleep(poll_interval)


class Verdict(BaseModel):
    content_id: int
    policy_name: Optional[str] = None
    content_text: str
    scores: Dict[str, int]  # rule name -> 0 / 1 / 2
    details: str
    created_at: Any

    @classmethod
    def _from_content(cls, content: Content) -> "Verdict":
        raw = dict(content.verdict_data)
        details = raw.pop("details", "")

        # The backend keys verdicts by policy_rule_index (as a string) rather
        # than rule name, to avoid leaking internal DB ids to the LLM. Map
        # back to names here so the SDK-facing Verdict is index-free.
        scores: Dict[str, int] = {}
        if content._policy is not None:
            index_to_name = {
                str(r.policy_rule_index): r.name for r in content._policy.rules.values()
            }
            for key, value in raw.items():
                scores[index_to_name.get(key, key)] = value
        else:
            scores = raw

        return cls(
            content_id=content.id,
            policy_name=content._policy.name if content._policy else None,
            content_text=content.text,
            scores=scores,
            details=details,
            created_at=content.created_at,
        )

    @property
    def color(self) -> str:
        values = self.scores.values()
        if any(v == 2 for v in values):
            return "red"
        if any(v == 1 for v in values):
            return "yellow"
        return "green"

    def __getitem__(self, rule_name: str) -> int:
        return self.scores[rule_name]

    def dict(self, *, as_string: bool = False):
        """Return this verdict as a dict (default), or a JSON string if as_string=True."""
        if as_string:
            return self.model_dump_json(indent=2)
        return self.model_dump()

    def json(self, *, as_dict: bool = False):
        """Return this verdict as a JSON string (default), or a dict if as_dict=True."""
        if as_dict:
            return self.model_dump()
        return self.model_dump_json(indent=2)

    def summary(self) -> None:
        """Pretty-print this verdict. Prints; returns None -- this is for display, not data."""
        from ._render import render_verdict_summary
        render_verdict_summary(self)