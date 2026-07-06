<p align="center">
  <img src="../frontend/assets/sdk_logo.jpg" alt="twelveangrymen logo" width="180" />
</p>

<h1 align="center">twelveangrymen</h1>
<p align="center"><strong>The official Python SDK for Jury</strong> — AI-powered content moderation, with a client that thinks like an ORM.</p>

<p align="center">
  <img alt="python" src="https://img.shields.io/badge/python-3.10%2B-blue">
  <img alt="style" src="https://img.shields.io/badge/style-sync--first-informational">
  <img alt="status" src="https://img.shields.io/badge/status-active--development-yellow">
  <img alt="built with" src="https://img.shields.io/badge/built%20with-httpx%20%7C%20pydantic%20%7C%20rich-9cf">
</p>

```python
import twelveangrymen as jury

client = jury.Jury(api_key="jk_...")
policy = client.policies.get("Community Guidelines")

verdict = policy.evaluate("some user-submitted text")
verdict.summary()
```

```
╭─ Community Guidelines — GREEN ─╮
│        😊 😊 😊 😊             │
│        😊 😊 😊 😊             │
│        😊 😊 😊 😊             │
│ ┏━━━━━━━━━━━━━┳━━━━━━━━━┓      │
│ ┃ Rule        ┃ Verdict ┃      │
│ ┡━━━━━━━━━━━━━╇━━━━━━━━━┩      │
│ │ Hate Speech │  clear  │      │
│ └─────────────┴─────────┘      │
│                                │
│ No issues found.               │
╰────────────────────────────────╯
```

---

## Why "twelveangrymen"?

Twelve jurors deliberate over a single verdict, weighing evidence rule by rule until they reach a decision. That's exactly what Jury's moderation engine does: a piece of content is weighed against every rule in a policy, and the aggregate of those individual judgments — clear, uncertain, or a violation — becomes the verdict. The name is a wink at that, and `verdict.summary()` leans into it: twelve little faces, all wearing whatever the jury decided.

## Table of contents

- [Install](#install)
- [Quickstart](#quickstart)
- [Core concepts](#core-concepts)
  - [Policies and rules](#policies-and-rules)
  - [Name-based access](#name-based-access)
  - [Index-based rule access](#index-based-rule-access)
- [The commit model](#the-commit-model)
  - [Lifecycle states](#lifecycle-states)
  - [Partial commit failures](#partial-commit-failures)
- [Evaluating content](#evaluating-content)
- [Verdicts](#verdicts)
- [Pretty-printing](#pretty-printing)
- [Error handling](#error-handling)
- [Object lifetime & tombstoning](#object-lifetime--tombstoning)
- [Full API reference](#full-api-reference)
- [Design notes for the curious](#design-notes-for-the-curious)
- [Known limitations](#known-limitations)
- [Roadmap](#roadmap)

---

## Install

Not published to PyPI — install directly from GitHub. The SDK lives in the `sdk/` subdirectory of the main Jury monorepo, so the install command points there explicitly:

```bash
pip install "git+https://github.com/MohamedFarouk94/jury.git#subdirectory=sdk"
```

To pick up changes after an update (plain `pip install` won't re-pull an already-satisfied package):

```bash
pip install --upgrade --force-reinstall --no-deps "git+https://github.com/MohamedFarouk94/jury.git#subdirectory=sdk"
```

## Quickstart

```python
import twelveangrymen as jury

# Reads JURY_API_KEY from the environment if not passed explicitly
client = jury.Jury(api_key="jk_...")

# Get-or-create is a natural pattern, since policy names are unique per user
try:
    policy = client.policies.create(name="Community Guidelines")
except jury.ConflictError:
    policy = client.policies.get("Community Guidelines")

policy.add_rule("Hate Speech", "No content attacking people based on protected traits.")
policy.add_rule("Spam", "No unsolicited promotional content.")
policy.commit()

verdict = policy.evaluate("You people don't belong here.")
verdict.summary()
```

## Core concepts

### Policies and rules

A **policy** is a named set of moderation **rules**. Each rule scores a piece of content on a 0–2 scale — clear, possible violation, clear violation — and the policy's overall verdict color is derived from the worst score across all its rules:

| Any rule scores... | Verdict color |
|---|---|
| all 0s | 🟢 green |
| a 1, no 2s | 🟡 yellow |
| any 2 | 🔴 red |

### Name-based access

Both policy names (per user) and rule names (per policy) are unique by design on the backend, so the SDK treats **name as the natural key** rather than exposing internal database ids:

```python
policy = client.policies.get("Community Guidelines")
rule = policy.get_rule("Hate Speech")
```

This is deliberately method-based (`get(name)` / `get_rule(name)`) rather than dict-style (`client.policies["name"]`) — it reads more explicitly as "go fetch this," which matters once you know some of these calls involve staged state rather than a live lookup (see below). Rules are stored internally as a `name -> Rule` dict for the same reason, so lookups by name are still O(1) — you're not scanning a list on every access.

### Index-based rule access

Jury's moderation engine sends each rule to the LLM tagged with its position within the policy (`policy_rule_index`). The SDK mirrors that with attribute-style access:

```python
first_rule  = policy.rule_1
second_rule = policy.rule_2
```

Accessing an index that doesn't exist raises `RuleDoesNotExistError`:

```python
policy.rule_13  # RuleDoesNotExistError: Policy 'Community Guidelines' has no
                # rule at index 13 (it currently has 2 committed rule(s)).
```

> **Note:** the backend re-sequences indices when a rule is deleted (deleting rule 2 of 4 makes the old rule 3 become the new rule 2). So `rule_N` means *"whichever rule currently holds slot N,"* not a stable identity over time — the same way `policy_rule_index` behaves server-side. Only **committed** rules occupy a slot; a rule staged via `add_rule()` but not yet committed has no index yet.

## The commit model

This is the part of the SDK that looks the least like a typical REST wrapper and the most like an ORM session — and that's intentional. Rule changes are **staged locally** and only sent to the server when you call `commit()`, the same way SQLAlchemy or Django track unsaved model changes:

```python
policy = client.policies.get("Community Guidelines")

policy.add_rule("Off-topic", "No content unrelated to the community.")     # staged
policy.get_rule("Spam").update(description="Tightened wording.")          # staged
policy.get_rule("Old Rule").delete()                                       # staged

policy.evaluate("some text")   # raises UncommittedChangesError --
                                # evaluating against rules that don't match
                                # the server yet would be evaluating against
                                # the wrong policy.

policy.commit()                # now everything is pushed, in one call
verdict = policy.evaluate("some text")  # works
```

Nothing touches the network until `commit()` — inspect what's pending any time with `policy.has_uncommitted_changes()`, and drop it all with `policy.discard_changes()` (which reloads clean state from the server).

### Lifecycle states

Every `Rule` moves through a small state machine, and `policy.summary()` shows you exactly where each one stands:

```
╭──────────────────────── Community Guidelines ─────────────────────────╮
│ General-purpose moderation policy                                     │
│                                                                        │
│  #   Name          Description                        Status              │
│  1   Hate Speech   No attacks on protected traits.     committed          │
│  2   Spam          Updated: no promo links...          edited (uncommitted)│
│  –   Off-topic     No content unrelated to community.  new (uncommitted)  │
╰──────────────────── 2 committed rule(s), 1 staged ─────────────────────╯
```

| State | Meaning |
|---|---|
| `pending` | staged as new via `add_rule()`, no server id yet |
| `persistent` | matches the server, clean |
| `dirty` | persistent, but locally edited via `update()` |
| `pending_delete` | persistent, but staged for deletion via `delete()` |
| `detached` | gone — deleted, discarded, or found stale; the object refuses further use (see [tombstoning](#object-lifetime--tombstoning)) |

`commit()` applies staged changes in a fixed order — **deletes, then updates, then creates** — so that, for example, renaming a rule into a name just freed by a delete in the same commit succeeds rather than colliding.

### Partial commit failures

The backend has no batch/transactional endpoint, so `commit()` sends each staged change as its own HTTP request — it is **not atomic**. If you and a teammate (or another script, or the dashboard) edit the same policy at the same time, some of your staged changes might land and others might not:

```python
try:
    policy.commit()
except jury.PartialCommitError as e:
    print("Succeeded:", e.succeeded)  # [("delete", "Old Rule")]
    print("Failed:", e.failed)        # [("update", "Spam", ConflictError(...))]
    # Failed changes remain staged -- fix the conflict and call commit() again,
    # or policy.discard_changes() to drop them and reload from the server.
```

Two conflict outcomes are handled with deliberate asymmetry, because they mean different things:

- **Deleting something already deleted by someone else** → treated as **success**. Your intent — "this rule shouldn't exist" — is already satisfied.
- **Updating something deleted by someone else** → a genuine **failure**. Your edit has nowhere to land, and it's reported so you know it was lost.

## Evaluating content

```python
# Blocks and polls internally until the verdict resolves (default)
verdict = policy.evaluate("some text")

# Non-blocking, for use in a server/request context
content = policy.evaluate("some text", wait=False)
# ... later ...
verdict = content.wait(timeout=15)

# Tune the polling behavior
verdict = policy.evaluate("some text", timeout=45, poll_interval=1.0)
```

If the verdict doesn't resolve in time, `evaluate()`/`wait()` raise `EvaluationTimeoutError` (carrying `.content_id`, so you can check on it later rather than losing track of the submission).

## Verdicts

```python
verdict.color            # "green" | "yellow" | "red"
verdict["Hate Speech"]   # 0, 1, or 2 -- score for a specific rule
verdict.details          # the model's reasoning, in prose
verdict.dict()           # {"content_id": ..., "scores": {...}, ...}
verdict.dict(as_string=True)  # same, as a JSON string
verdict.json()           # JSON string (default)
verdict.json(as_dict=True)   # same, as a dict
```

Full moderation history for a policy:

```python
for past in policy.past_verdicts():
    print(past.color, past.details)

# Also include submissions still processing or that failed:
policy.past_verdicts(include_pending=True)
```

## Pretty-printing

Both `Policy` and `Verdict` have a `.summary()` — prints directly to the terminal (returns `None`, this is for humans, not data), rendered with [`rich`](https://github.com/Textualize/rich) when it's installed and falling back to clean plain text otherwise:

```python
policy.summary()   # policy name/description + a table of all rules and their staging status
verdict.summary()  # twelve faces, all wearing the verdict's sentiment, + a per-rule score table
```

## Error handling

```
JuryError
├── MissingAPIKeyError
├── APIConnectionError
├── AuthenticationError        (401)
├── NotFoundError              (404 -- a fresh lookup found nothing)
├── ResourceGoneError          ("this used to exist")
│   ├── DeletedResourceError   (you deleted it yourself; purely local, no network call)
│   └── StaleReferenceError    (the server said it's gone, unexpectedly)
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
```

Every exception carries the original `.status_code` and `.detail` from the API where applicable, so you're never stuck parsing a message string:

```python
try:
    policy.evaluate("some text")
except jury.QuotaExceededError as e:
    print(f"Hit the daily limit: {e.detail}")
```

## Object lifetime & tombstoning

Once a `Policy` or `Rule` is deleted — by you, or found gone unexpectedly — **every further method call on that same Python object raises immediately**, rather than silently doing nothing or surfacing a confusing error three calls later:

```python
policy.delete()
policy.evaluate("text")   # DeletedResourceError -- no network call, the SDK already knows

# Deleting a policy cascades: every Rule object you were holding from it
# is tombstoned too, since they genuinely no longer exist.
rule.update(description="...")  # DeletedResourceError
```

If the server tells you something's gone that you didn't expect — a teammate deleted it from the dashboard mid-session — you get `StaleReferenceError` instead, so you can distinguish "I did this" from "this surprised me":

```python
try:
    rule.update(description="...")
except jury.StaleReferenceError:
    print("Someone else deleted this rule -- refreshing.")
    policy.refresh()
```

## Full API reference

### `Jury(api_key=None, base_url=None, timeout=30.0, max_retries=2)`
Entry point. Reads `JURY_API_KEY` / `JURY_BASE_URL` from the environment if not passed explicitly. Supports `with jury.Jury() as client:` for clean connection-pool teardown.

### `client.policies`
- `.create(name, description=None) -> Policy`
- `.get(name) -> Policy` — raises `NotFoundError` if no policy has that name
- `.list() -> list[Policy]`

### `Policy`
- `.get_rule(name) -> Rule`
- `.rule_1`, `.rule_2`, ... — index-based access to committed rules
- `.add_rule(name, description) -> Rule` — staged, not sent until `commit()`
- `.commit()` — push all staged rule changes; may raise `PartialCommitError`
- `.discard_changes()` — drop all staged changes, reload from the server
- `.refresh(force=False)` — reload from the server; raises `UncommittedChangesError` unless `force=True` or nothing is staged
- `.has_uncommitted_changes() -> bool`
- `.evaluate(text, wait=True, timeout=30.0, poll_interval=0.5) -> Verdict | Content`
- `.past_verdicts(include_pending=False) -> list[Verdict]`
- `.summary()` — pretty-print
- `.delete()` — deletes on the server; tombstones this policy and all its rules locally

### `Rule`
- `.update(name=None, description=None)` — staged; requires at least one argument
- `.delete()` — staged

### `Content` (returned by `evaluate(wait=False)`)
- `.is_resolved`, `.failed` — status properties
- `.refresh() -> Content`
- `.wait(timeout=30.0, poll_interval=0.5) -> Verdict`

### `Verdict`
- `.color` — `"green" | "yellow" | "red"`
- `[rule_name]` — score for a specific rule (0/1/2)
- `.scores`, `.details`, `.content_id`, `.content_text`, `.policy_name`, `.created_at`
- `.dict(as_string=False)`, `.json(as_dict=False)`
- `.summary()` — pretty-print

## Design notes for the curious

A few choices that came out of deliberately thinking through failure modes before writing code, rather than after:

- **Unit-of-work over immediate writes.** Rule changes are staged and only pushed on `commit()`, mirroring SQLAlchemy's session model. This mostly exists so `evaluate()` can refuse to run against a policy whose local rules don't match what's live on the server — a correctness guarantee that's impossible if every `.update()` hits the network immediately.
- **Tombstoning via `__getattribute__`, not a manual flag.** A deleted object could have been given an `is_deleted` boolean that every method checks — but that's one `if` statement someone eventually forgets to add to a new method. Overriding `__getattribute__` with a small allowlist (repr, name, id) makes "raise on any further use" impossible to bypass by accident.
- **Idempotent delete, asymmetric update, during `commit()`.** Deleting something already gone is treated as success (your intent was satisfied); updating something already gone is a real failure (your edit is lost). Same "not found" response from the server, deliberately different outcomes, because the two operations mean different things when the target has vanished.
- **Rule renaming re-keys its parent's lookup table.** `policy.rules` is a `name -> Rule` dict for O(1) lookups, which means a rename has to pop the old key and insert the new one — handled inside `Rule.update()` via a callback into the owning `Policy`, so the object you're holding and the collection it lives in never disagree about its name.
- **API keys are hashed, not encrypted.** Keys are high-entropy random strings generated server-side (unlike user passwords), so they're stored as a SHA-256 digest rather than run through bcrypt — a deliberate choice to allow direct-hash lookup instead of a linear bcrypt comparison against every stored key.
- **Sync-first, not sync-only forever.** The transport is built on `httpx` specifically because it has a matching async client with the same API shape — an `AsyncJury` can be added later without redesigning anything above the transport layer.

## Known limitations

- **`commit()` is not atomic.** No batch endpoint exists server-side yet, so a commit is several independent requests, not a transaction. See [Partial commit failures](#partial-commit-failures).
- **`list()` and name-based `get()` are not O(1) round trips.** Policy names aren't looked up server-side yet, so `get(name)` lists all policies and filters client-side, then fetches the match by id (2 requests). `list()` similarly fetches full details per policy (N+1). Fine at today's scale; worth a dedicated backend route if policy counts grow large.
- **`rule_N` reflects local state as of the last fetch/commit**, not a live server call — by design (no hidden I/O on attribute access), but it means a concurrent change elsewhere won't be visible until you `refresh()`.
- **API key management is dashboard-only.** This SDK authenticates with a key; it doesn't create, list, or revoke them.

## Roadmap

- [ ] Async client (`AsyncJury`)
- [ ] Backend route for direct policy-by-name lookup (removing the 2-round-trip `get()`/`list()` cost)
- [ ] CLI built on top of this SDK