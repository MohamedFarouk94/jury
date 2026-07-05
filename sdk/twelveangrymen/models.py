"""
Design note: Policy and Rule are plain Python classes, not Pydantic models.
They carry mutable lifecycle state (staged/dirty/deleted), a back-reference to
the HTTP transport, and need a custom __getattribute__ to enforce "no further
use after this object is known to be gone." Fighting Pydantic's own attribute
machinery to get that would cost more than it's worth. Content and Verdict, by
contrast, are close to pure data results, so Verdict is a Pydantic model
(models.py -- see verdict.py) and gets .dict()/.json() essentially for free.
"""

import enum
import re
import time

from . import exceptions as exc


class _State(enum.Enum):
    PENDING = "pending"                # staged as new, no server id yet
    PERSISTENT = "persistent"          # matches the server, clean
    DIRTY = "dirty"                    # persistent, locally edited, not committed
    PENDING_DELETE = "pending_delete"  # persistent, staged for deletion
    DETACHED = "detached"              # no longer usable -- deleted, stale, or discarded


class _TombstoneGuard:
    """
    Mixin that makes an object unusable after it's known to be gone, instead of
    relying on every caller to remember to check a `.is_deleted` flag. A small
    allowlist stays reachable for debugging/inspection (repr, name, id, state).
    """

    _ALLOWED_AFTER_DETACH = frozenset({"_state", "_detach_reason", "name", "id"})

    def __getattribute__(self, item):
        get = object.__getattribute__
        if item.startswith("__") or item in get(self, "_ALLOWED_AFTER_DETACH"):
            return get(self, item)

        if get(self, "_state") == _State.DETACHED:
            kind = type(self).__name__
            name = get(self, "name")
            reason = get(self, "_detach_reason")
            if reason == "deleted":
                raise exc.DeletedResourceError(
                    f"This {kind} ('{name}') was already deleted. It can no longer be used -- "
                    f"fetch a new reference if you need it again."
                )
            if reason == "discarded":
                raise exc.StaleReferenceError(
                    f"This {kind} ('{name}') was replaced by a refresh()/discard_changes() call. "
                    f"Fetch a fresh reference instead of reusing this object."
                )
            raise exc.StaleReferenceError(
                f"This {kind} ('{name}') no longer exists on the server -- "
                f"it was likely deleted elsewhere."
            )

        return get(self, item)


class Rule(_TombstoneGuard):
    def __init__(self, name, description, *, id=None, policy_rule_index=None,
                 created_at=None, policy=None, transport=None):
        self._detach_reason = None
        self.id = id
        self.name = name
        self.description = description
        self.policy_rule_index = policy_rule_index
        self.created_at = created_at
        self._policy = policy
        self._transport = transport
        self._state = _State.PERSISTENT if id is not None else _State.PENDING

    def __repr__(self):
        return (f"<Rule name={self.name!r} index={self.policy_rule_index!r} "
                f"state={self._state.value}>")

    # ── staged mutation ───────────────────────────────────────────────────

    def update(self, *, name=None, description=None):
        """Stage a name/description change. Not sent to the server until policy.commit()."""
        if name is None and description is None:
            raise ValueError("update() requires at least one of name= or description=.")

        if self._state == _State.PENDING_DELETE:
            raise ValueError(
                "This rule is staged for deletion; it can't also be updated. "
                "Call policy.discard_changes() first if you want to keep it."
            )

        old_name = self.name

        if self._state == _State.PENDING:
            # Never hit the server yet -- just mutate the staged values directly.
            if description is not None:
                self.description = description
            if name is not None and name != old_name:
                if self._policy is not None:
                    self._policy._rekey_rule(self, old_name, name)
                self.name = name
            return

        if description is not None:
            self.description = description
        if name is not None and name != old_name:
            if self._policy is not None:
                self._policy._rekey_rule(self, old_name, name)
            self.name = name

        self._state = _State.DIRTY

    def delete(self):
        """Stage this rule for deletion. Not sent to the server until policy.commit()."""
        if self._state == _State.PENDING:
            # Never existed on the server -- just unstage it, nothing to commit.
            if self._policy is not None:
                self._policy._unstage_new_rule(self)
            self._state = _State.DETACHED
            self._detach_reason = "deleted"
            return
        self._state = _State.PENDING_DELETE

    # ── internal: applied by Policy.commit() / Policy.refresh() ────────────

    def _mark_committed_create(self, api_data):
        self.id = api_data["id"]
        self.policy_rule_index = api_data["policy_rule_index"]
        self.created_at = api_data["created_at"]
        self._state = _State.PERSISTENT

    def _mark_committed_update(self, api_data):
        self.policy_rule_index = api_data["policy_rule_index"]
        self._state = _State.PERSISTENT

    def _mark_committed_delete(self):
        self._state = _State.DETACHED
        self._detach_reason = "deleted"

    def _mark_gone(self):
        self._state = _State.DETACHED
        self._detach_reason = "stale"

    def _mark_discarded(self):
        self._state = _State.DETACHED
        self._detach_reason = "discarded"


_RULE_INDEX_RE = re.compile(r"rule_(\d+)")


class Policy(_TombstoneGuard):
    def __init__(self, id, name, description, owner_id, created_at, transport):
        self._detach_reason = None
        self._state = _State.PERSISTENT
        self.id = id
        self.name = name
        self.description = description
        self.owner_id = owner_id
        self.created_at = created_at
        self._transport = transport
        self.rules = {}         # name -> Rule (committed + staged-new, combined)
        self._pending_new = []  # Rules with state PENDING, in creation order

    @classmethod
    def _from_api(cls, data, transport):
        policy = cls(
            id=data["id"], name=data["name"], description=data.get("description"),
            owner_id=data.get("owner_id"), created_at=data["created_at"], transport=transport,
        )
        for r in data.get("rules", []):
            policy.rules[r["name"]] = Rule(
                name=r["name"], description=r["description"], id=r["id"],
                policy_rule_index=r["policy_rule_index"], created_at=r["created_at"],
                policy=policy, transport=transport,
            )
        return policy

    def __repr__(self):
        return f"<Policy name={self.name!r} rules={len(self.rules)} state={self._state.value}>"

    # ── rule access ───────────────────────────────────────────────────────

    def get_rule(self, name):
        rule = self.rules.get(name)
        if rule is None:
            raise exc.RuleDoesNotExistError(f"Policy '{self.name}' has no rule named '{name}'.")
        return rule

    def __getattr__(self, item):
        # Only invoked when normal lookup fails, so it never shadows real
        # attributes -- this is purely the rule_1 / rule_2 / ... convenience.
        match = _RULE_INDEX_RE.fullmatch(item)
        if not match:
            raise AttributeError(item)

        index = int(match.group(1))
        # Index access only ever reflects committed (persistent/dirty) rules --
        # a rule staged-but-not-yet-committed has no server-assigned index yet.
        # Note: policy_rule_index is server-assigned and gets re-sequenced on
        # delete, so rule_N means "whichever rule currently holds slot N", not
        # a stable identity across time.
        for rule in self.rules.values():
            if rule._state in (_State.PERSISTENT, _State.DIRTY) and rule.policy_rule_index == index:
                return rule

        committed_count = sum(
            1 for r in self.rules.values() if r._state in (_State.PERSISTENT, _State.DIRTY)
        )
        raise exc.RuleDoesNotExistError(
            f"Policy '{self.name}' has no rule at index {index} "
            f"(it currently has {committed_count} committed rule(s))."
        )

    def add_rule(self, name, description):
        """Stage a new rule. Not sent to the server until commit()."""
        if name in self.rules:
            raise ValueError(f"A rule named '{name}' is already staged or present on this policy.")
        rule = Rule(name=name, description=description, policy=self, transport=self._transport)
        self.rules[name] = rule
        self._pending_new.append(rule)
        return rule

    def _rekey_rule(self, rule, old_name, new_name):
        if new_name in self.rules and self.rules[new_name] is not rule:
            raise ValueError(f"A rule named '{new_name}' is already staged or present on this policy.")
        self.rules.pop(old_name, None)
        self.rules[new_name] = rule

    def _unstage_new_rule(self, rule):
        self.rules.pop(rule.name, None)
        if rule in self._pending_new:
            self._pending_new.remove(rule)

    # ── staging introspection ────────────────────────────────────────────

    def _pending_changes(self):
        return {
            "new": [r.name for r in self.rules.values() if r._state == _State.PENDING],
            "dirty": [r.name for r in self.rules.values() if r._state == _State.DIRTY],
            "pending_delete": [r.name for r in self.rules.values() if r._state == _State.PENDING_DELETE],
        }

    def has_uncommitted_changes(self):
        pc = self._pending_changes()
        return bool(pc["new"] or pc["dirty"] or pc["pending_delete"])

    # ── commit / discard ─────────────────────────────────────────────────

    def commit(self):
        """
        Push all staged rule changes to the server. Order is delete -> update
        -> create, so a rename into a name just freed by a delete in the same
        commit succeeds. This is NOT atomic -- the backend has no batch/
        transaction endpoint, so each change is its own request. If some
        succeed and others fail, PartialCommitError is raised; anything that
        failed stays staged so you can resolve it and commit() again.
        """
        succeeded, failed = [], []

        for rule in [r for r in self.rules.values() if r._state == _State.PENDING_DELETE]:
            try:
                self._transport.request("DELETE", f"/policies/{self.id}/rules/{rule.id}")
                rule._mark_committed_delete()
                del self.rules[rule.name]
                succeeded.append(("delete", rule.name))
            except exc.NotFoundError:
                # Already gone -- that's the outcome we wanted anyway. Not a failure.
                rule._mark_committed_delete()
                del self.rules[rule.name]
                succeeded.append(("delete", rule.name))
            except exc.JuryError as e:
                failed.append(("delete", rule.name, e))

        for rule in [r for r in self.rules.values() if r._state == _State.DIRTY]:
            try:
                resp = self._transport.request(
                    "PUT", f"/policies/{self.id}/rules/{rule.id}",
                    json={"name": rule.name, "description": rule.description},
                )
                rule._mark_committed_update(resp.json())
                succeeded.append(("update", rule.name))
            except exc.NotFoundError as e:
                # Someone else deleted the rule out from under this edit -- the
                # edit genuinely has nowhere to land, so this is a real failure.
                rule._mark_gone()
                del self.rules[rule.name]
                failed.append(("update", rule.name, e))
            except exc.JuryError as e:
                failed.append(("update", rule.name, e))

        for rule in list(self._pending_new):
            try:
                resp = self._transport.request(
                    "POST", f"/policies/{self.id}/rules/",
                    json={"name": rule.name, "description": rule.description},
                )
                rule._mark_committed_create(resp.json())
                self._pending_new.remove(rule)
                succeeded.append(("create", rule.name))
            except exc.JuryError as e:
                failed.append(("create", rule.name, e))

        if failed:
            raise exc.PartialCommitError(
                f"{len(succeeded)} change(s) committed, {len(failed)} failed. "
                f"Failed changes remain staged -- resolve and call commit() again, "
                f"or discard_changes() to drop them.",
                succeeded=succeeded, failed=failed,
            )

    def discard_changes(self):
        """Drop all staged (uncommitted) rule changes and reload from the server."""
        self.refresh(force=True)

    def refresh(self, *, force=False):
        """
        Reload this policy's rules from the server. Raises UncommittedChangesError
        if there are staged edits, unless force=True -- in which case they're
        discarded. Every Rule object previously held from this policy is
        tombstoned (even ones with no pending changes), since refresh replaces
        them wholesale with fresh objects reflecting current server state.
        """
        if not force and self.has_uncommitted_changes():
            raise exc.UncommittedChangesError(
                "This Policy has uncommitted local changes. Call commit() to save them, "
                "or refresh(force=True) / discard_changes() to drop them and reload.",
                pending_changes=self._pending_changes(),
            )

        try:
            resp = self._transport.request("GET", f"/policies/{self.id}")
        except exc.NotFoundError as e:
            self._state = _State.DETACHED
            self._detach_reason = "stale"
            raise exc.StaleReferenceError(
                f"Policy '{self.name}' no longer exists on the server."
            ) from e

        data = resp.json()
        self.name = data["name"]
        self.description = data.get("description")

        for rule in self.rules.values():
            rule._mark_discarded()
        self.rules = {}
        self._pending_new = []

        for r in data.get("rules", []):
            self.rules[r["name"]] = Rule(
                name=r["name"], description=r["description"], id=r["id"],
                policy_rule_index=r["policy_rule_index"], created_at=r["created_at"],
                policy=self, transport=self._transport,
            )

    # ── policy-level actions ─────────────────────────────────────────────

    def delete(self):
        """Delete this policy (and its rules, contents) on the server."""
        try:
            self._transport.request("DELETE", f"/policies/{self.id}")
        except exc.NotFoundError:
            pass  # already gone -- that's the outcome we wanted anyway
        for rule in self.rules.values():
            rule._mark_committed_delete()
        self.rules = {}
        self._pending_new = []
        self._state = _State.DETACHED
        self._detach_reason = "deleted"

    def evaluate(self, content: str, *, wait: bool = True, timeout: float = 30.0,
                 poll_interval: float = 0.5):
        """
        Submit content for moderation against this policy. By default, blocks
        and polls until the verdict resolves (or `timeout` elapses), returning
        a Verdict. Pass wait=False for a non-blocking Content handle instead.

        Raises UncommittedChangesError if this Policy has staged rule changes
        that haven't been committed -- evaluating against a policy that
        doesn't yet match the server would be evaluating against the wrong
        rules.
        """
        from .verdict import Content  # local import to avoid a circular import

        if self.has_uncommitted_changes():
            raise exc.UncommittedChangesError(
                "Cannot evaluate through a Policy with uncommitted rule changes. "
                "Call commit() first, or discard_changes() to drop them.",
                pending_changes=self._pending_changes(),
            )

        resp = self._transport.request(
            "POST", "/contents/", json={"text": content, "policy_id": self.id}
        )
        content_obj = Content._from_api(resp.json(), self._transport, policy=self)

        if not wait:
            return content_obj
        return content_obj.wait(timeout=timeout, poll_interval=poll_interval)

    def summary(self) -> None:
        """Pretty-print this policy and its rules. Prints; returns None."""
        from ._render import render_policy_summary
        render_policy_summary(self)

    def past_verdicts(self, *, include_pending: bool = False):
        """
        Return this policy's resolved verdicts as a list of Verdict objects,
        most-recent-last (matching the backend's chronological ordering).
        Pass include_pending=True to also get raw Content objects for
        submissions that are still processing or failed.
        """
        from .verdict import Content, Verdict  # local import to avoid a circular import

        resp = self._transport.request("GET", f"/contents/policy/{self.id}")
        results = []
        for data in resp.json():
            content_obj = Content._from_api(data, self._transport, policy=self)
            if content_obj.is_resolved:
                results.append(Verdict._from_content(content_obj))
            elif include_pending:
                results.append(content_obj)
        return results