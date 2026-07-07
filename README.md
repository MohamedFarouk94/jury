<p align="center">
  <img src="./frontend/assets/logo.jpg" alt="Jury logo" width="120" />
</p>

<h1 align="center">⚖️ Jury</h1>
<p align="center"><strong>Define moderation policies in plain English. Get auditable, per-rule AI verdicts — not a black-box boolean.</strong></p>

<p align="center">
  <img alt="python" src="https://img.shields.io/badge/python-3.10%2B-blue">
  <img alt="backend" src="https://img.shields.io/badge/backend-FastAPI%20%2B%20LangChain-009688">
  <img alt="frontend" src="https://img.shields.io/badge/frontend-vanilla%20JS%2C%20zero%20build-f7df1e">
  <img alt="sdk" src="https://img.shields.io/badge/sdk-twelveangrymen-9cf">
  <img alt="status" src="https://img.shields.io/badge/status-active--development-yellow">
</p>

<p align="center">
  🖥️ <a href="https://jury-livid.vercel.app"><strong>Live app</strong></a> ·
  📖 <a href="./backend">Backend API</a> ·
  🌐 <a href="./frontend">Frontend</a> ·
  📦 <a href="./sdk">Python SDK</a> ·
  💻 CLI <em>(planned)</em>
</p>

---

## What is this?

Most moderation tools give you a single "is this safe?" boolean. **Jury** doesn't. You write a policy — a plain-English set of rules — and every piece of content is scored **independently against each rule** on a 3-level scale (no violation / possible violation / clear violation). The result is a verdict you can actually audit: which rule triggered, how confidently, and why.

```
User → Policy → Rule(s)
              → Content → Verdict
```

| Score | Meaning |
|---|---|
| `0` | No violation |
| `1` | Possible violation (ambiguous) |
| `2` | Clear violation |

Verdicts roll up into one glance: 🟢 all-clear, 🟡 something ambiguous, 🔴 something clear-cut.

This repo is a **monorepo** containing everything end to end — the API, the web client, and the SDK developers use to talk to it programmatically.

---

## Why this repo is worth a closer look

This isn't a tutorial CRUD app. It's built the way a small production service actually gets built — with the tradeoffs, security hardening, and design deliberation that implies:

- **A real auth model, not just JWTs.** JWTs and hashed, revocable API keys (`jk_...`) share a single `get_current_user` dependency, differentiated by prefix — because JWTs and API keys solve genuinely different problems (session identity vs. programmatic, non-expiring access), and quota is enforced per-user so minting keys can't be used to dodge rate limits. See [Authentication](./backend#authentication).
- **An SDK designed like an ORM, on paper first.** The [`twelveangrymen`](./sdk) SDK stages changes locally and only hits the network on `.commit()` — a SQLAlchemy-style unit-of-work model, complete with `PartialCommitError` handling for a backend that has no transactional batch endpoint, and tombstoning via `__getattribute__` so a deleted object can never be silently misused.
- **Security treated as a default, not a checkbox.** No app boot without a `SECRET_KEY`. No plaintext API keys, ever — only SHA-256 hashes. Brute-force lockouts. Correct `401`s instead of leaking `500`s on malformed tokens. Per-owner uniqueness enforced at the database layer, not just in application code.
- **A framework-free frontend that doesn't feel like one.** The [frontend](./frontend) is plain ES modules and the native DOM — no React, no bundler — yet still ships live polling, optimistic updates, mobile drawer navigation, and a GitHub/Stripe-style "shown once" secrets UX. A demonstration that the fundamentals scale further than people assume.
- **Design-before-code, consistently.** Each part of this repo — auth strategy, the SDK's error hierarchy, the commit model's conflict semantics — went through multiple rounds of deliberate API-surface design before a line of implementation was written.

If you're a hiring team skimming this: the individual READMEs linked throughout go deep on rationale, not just usage — that's intentional.

---

## Architecture

```
┌─────────────────────┐        ┌──────────────────────┐
│   Frontend (SPA)      │        │   Python SDK           │
│   Vanilla JS, Vercel   │        │   twelveangrymen        │
└──────────┬───────────┘        └──────────┬───────────┘
           │                                │
           │        Authorization: Bearer <JWT | jk_...>
           └───────────────┬────────────────┘
                            ▼
                  ┌───────────────────────┐
                  │   FastAPI backend       │
                  │   routes / core / utils │
                  │   (Hugging Face Spaces) │
                  └───────────┬────────────┘
                              │
                    ┌─────────┴─────────┐
                    │                    │
                    ▼                    ▼
              SQLite (/data)      Groq LLM (via LangChain)
```

Both the browser frontend and the SDK talk to the **same** backend through the **same** `Authorization: Bearer` header — the server tells credential types apart by a `jk_` prefix, so there's exactly one auth code path to reason about, not two.

---

## Repo structure

```
jury/
├── backend/     → FastAPI + SQLAlchemy + LangChain API, deployed on Hugging Face Spaces
├── frontend/    → Vanilla JS SPA, deployed on Vercel
├── sdk/         → twelveangrymen — the Python client SDK, installable via pip + GitHub
└── cli/         → (planned) command-line client built on the SDK
```

| Part | README | Live |
|---|---|---|
| Backend | [`backend/README.md`](./backend) | API docs at `/docs` on the deployed Space |
| Frontend | [`frontend/README.md`](./frontend) | [jury-livid.vercel.app](https://jury-livid.vercel.app) |
| SDK | [`sdk/README.md`](./sdk) | `pip install "git+https://github.com/MohamedFarouk94/jury.git#subdirectory=sdk"` |

---

## Quickstart

**Run the whole thing locally** — see each README for full detail:

```bash
git clone https://github.com/MohamedFarouk94/jury.git
cd jury

# 1. Backend
cd backend && pip install -r requirements.txt
# configure .env (see backend README) then:
uvicorn main:app --reload --port 7860

# 2. Frontend (in a new terminal)
cd ../frontend
python3 -m http.server 5500
# open http://localhost:5500

# 3. SDK, if you'd rather talk to it programmatically
pip install "git+https://github.com/MohamedFarouk94/jury.git#subdirectory=sdk"
```

```python
import twelveangrymen as jury

client = jury.Jury(api_key="jk_...")
policy = client.policies.get("Community Guidelines")
verdict = policy.evaluate("some user-submitted text")
verdict.summary()
```

---

## Tech stack

| Layer | Choice |
|---|---|
| **Backend** | FastAPI · SQLAlchemy · SQLite · `python-jose` (JWT) · `passlib`/bcrypt · LangChain · Groq (`llama-3.3-70b-versatile`) |
| **Frontend** | Vanilla JavaScript (ES modules) · plain CSS custom properties · no framework, no bundler |
| **SDK** | `httpx` (sync, with an async upgrade path already designed in) · `rich` for terminal pretty-printing |
| **Infrastructure** | Docker on Hugging Face Spaces (with a mounted Storage Bucket for persistence) · Vercel for the frontend |

---

## Engineering principles across the stack

A few things that show up in more than one part of this repo, because they were treated as project-wide defaults rather than one-off choices:

- **The policy owns the rules driving the logic** — `policy.check(content)` everywhere, not `content.check(policy)`, so `Content` stays a plain data object. This shaped the backend's route design and the SDK's method signatures identically.
- **No silent fallbacks around anything security-sensitive.** Missing `SECRET_KEY` crashes on boot rather than defaulting. API keys are stored hashed, never in retrievable form, in both the backend model and how the SDK is documented to use them.
- **Explicit over implicit, even when implicit is less code.** Structured logging uses route-level calls instead of middleware so failed logins are attributed correctly *before* auth resolves. The SDK's tombstoning overrides `__getattribute__` directly instead of relying on a boolean flag every method has to remember to check.
- **Documentation as a design artifact, not an afterthought.** Every README in this repo explains *why*, not just *how* — because the reasoning behind a decision is usually more interesting than the decision itself.

---

## Roadmap

- [ ] CLI (`cli/`), built on top of the SDK
- [ ] Async SDK client (`AsyncJury`) — the `httpx` transport was chosen specifically to make this a non-redesign
- [ ] Backend route for direct policy-by-name lookup, removing the SDK's current 2-round-trip `get()`
- [ ] Admin/stats monitoring endpoint

---

<p align="center"><em>Built by <a href="https://github.com/MohamedFarouk94">Mohamed Farouk</a>.</em></p>