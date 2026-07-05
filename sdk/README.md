# twelveangrymen

Python SDK for [Jury](https://mfarouk-jury-backend.hf.space) — AI-powered content moderation.

Not published to PyPI; install directly from GitHub.

## Install

```bash
pip install "git+https://github.com/MohamedFarouk94/jury.git#subdirectory=sdk"
```

## Quickstart

```python
import twelveangrymen as jury

client = jury.Jury(api_key="jk_...")  # or set JURY_API_KEY in the environment

# Get or create a policy (names are unique per user, so this is a safe pattern)
try:
    policy = client.policies.create(name="Community Guidelines")
except jury.ConflictError:
    policy = client.policies.get("Community Guidelines")

# Stage some rule changes -- nothing is sent yet
policy.add_rule("Hate Speech", "No content attacking people based on protected traits.")
policy.get_rule("Off-topic").update(description="Tightened wording.")

# Push staged changes to the server
policy.commit()

# Evaluate content (blocks and polls until the verdict resolves)
verdict = policy.evaluate("some user-submitted text")
verdict.summary()          # pretty-printed, color-coded
print(verdict.color)       # "green" | "yellow" | "red"
print(verdict["Hate Speech"])
print(verdict.json())      # JSON string
print(verdict.dict())      # plain dict

# Index-based rule access, mirroring what's sent to the LLM
first_rule = policy.rule_1

# Full moderation history for this policy
for past in policy.past_verdicts():
    print(past.color, past.details)
```

## Key design points

- **Sync only, for now.** Built on `httpx`, so an async client can be added later without a rewrite.
- **Name-based access.** Policies and rules are looked up by name (`client.policies.get(name)`, `policy.get_rule(name)`), not id — both are unique per owner/policy on the backend, so this is safe and much friendlier than juggling ids.
- **Staged commits.** `add_rule()`, `rule.update()`, and `rule.delete()` only change local state. Nothing hits the server until `policy.commit()`. `policy.evaluate()` refuses to run against a policy with uncommitted changes (`UncommittedChangesError`) so you never evaluate against rules that don't match what's live.
- **Commits aren't atomic.** The backend has no batch endpoint, so `commit()` sends each staged change as its own request. If some succeed and others fail (e.g. a concurrent edit from another script or the dashboard), you get `PartialCommitError` with `.succeeded` / `.failed` — failed changes stay staged so you can fix and retry.
- **Tombstoning.** Once you delete a `Policy` or `Rule` (or it's found gone unexpectedly), every further method call on that same Python object raises immediately — `DeletedResourceError` if you deleted it yourself, `StaleReferenceError` if the server surprised you. No silent zombie objects.
- **API keys are dashboard-only.** This SDK authenticates with a key; it doesn't create, list, or revoke them.