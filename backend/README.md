---
title: Jury Backend
emoji: ⚖️
colorFrom: indigo
colorTo: purple
sdk: docker
pinned: false
app_port: 7860
---

# ⚖️ Jury — AI Content Moderation API

**Jury** is a backend service that lets you define custom content moderation policies — made up of plain-English rules — and evaluate arbitrary text against them using an LLM. Instead of a single "is this safe?" boolean, every rule is scored independently on a 3-level violation scale, so you get a granular, auditable verdict rather than a black box.

Built with **FastAPI**, **SQLAlchemy**, and **LangChain** (via Groq), deployed on **Hugging Face Spaces**.

- 🖥️ **Live API:** deployed via this Space (Docker SDK, see `app_port` above)
- 🌐 **Frontend:** [jury-livid.vercel.app](https://jury-livid.vercel.app) — vanilla JS SPA, no framework
- 📦 **Python SDK:** [`twelveangrymen`](https://github.com/MohamedFarouk94/jury.git) (`#subdirectory=sdk`) — programmatic access with a SQLAlchemy-style unit-of-work model

---

## Table of Contents

- [How it works](#how-it-works)
- [Architecture](#architecture)
- [API reference](#api-reference)
- [Authentication](#authentication)
- [Security](#security)
- [Project structure](#project-structure)
- [Running locally](#running-locally)
- [Notable engineering decisions](#notable-engineering-decisions)
- [Tech stack](#tech-stack)

---

## How it works

The domain model is intentionally small and composable:

```
User → Policy → Rule(s)
              → Content → Verdict
```

1. A user creates a **Policy** (e.g. "Community Guidelines").
2. The policy is given one or more **Rules** in plain English (e.g. "No hate speech targeting protected groups").
3. **Content** (a piece of text) is submitted against a policy.
4. An LLM chain evaluates the content against *each rule independently* and returns a **Verdict**: for every rule, a score of

   | Score | Meaning |
   |---|---|
   | `0` | No violation |
   | `1` | Possible violation (ambiguous) |
   | `2` | Clear violation |

5. The frontend derives an overall color from the verdict: 🟢 green if every rule scores 0, 🟡 yellow if any rule scores 1 and none scores 2, 🔴 red if any rule scores 2.

Verdicts are computed as a **background task** — content is created and returned immediately with `verdict: null`, and the LLM call happens asynchronously, so the client polls or re-fetches once it's ready.

---

## Architecture

```
Client (frontend / SDK)
        │
        │  Authorization: Bearer <JWT or jk_... API key>
        ▼
   FastAPI app (main.py)
        │
        ├── routes/        → HTTP layer, request validation, ownership checks
        ├── utils/         → auth, API key hashing, quota enforcement
        ├── core/          → LangChain prompt + chain construction, Groq client
        ├── schemas/       → Pydantic request/response models
        └── models/        → SQLAlchemy ORM models + session management
                    │
                    ▼
              SQLite (jury.db)
```

A single `get_current_user` dependency resolves *either* a JWT *or* an API key from the same `Authorization: Bearer` header — see [Authentication](#authentication).

---

## API reference

All routes are mounted under `/api`.

### Auth — `/api/auth`

| Method | Path | Description |
|---|---|---|
| `POST` | `/signup` | Create an account. Password must be 8+ chars with upper, lower, digit, and special character. |
| `POST` | `/login` | Returns a JWT (`Bearer`, 7-day expiry). Locks the account for 15 minutes after 5 failed attempts. |

### Policies — `/api/policies`

| Method | Path | Description |
|---|---|---|
| `POST` | `/` | Create a policy. Names must be unique per user. |
| `GET` | `/` | List the current user's policies (summary view). |
| `GET` | `/{policy_id}` | Get a policy with its full ordered rule list. |
| `DELETE` | `/{policy_id}` | Delete a policy and cascade-delete its rules and content. |

### Rules — `/api/policies/{policy_id}/rules`

| Method | Path | Description |
|---|---|---|
| `POST` | `/` | Add a rule. Rule names must be unique within the policy. Assigned the next 1-based index. |
| `PUT` | `/{rule_id}` | Update a rule's name and/or description. |
| `DELETE` | `/{rule_id}` | Delete a rule; remaining rules are re-indexed to stay contiguous. |

### Content — `/api/contents`

| Method | Path | Description |
|---|---|---|
| `POST` | `/` | Submit content against a policy. Enforces the daily quota, then kicks off async verdict generation. |
| `GET` | `/policy/{policy_id}` | List all content submitted under a policy, oldest first. |
| `GET` | `/{content_id}` | Get a single piece of content and its verdict. |

### API Keys — `/api/api-keys`

| Method | Path | Description |
|---|---|---|
| `POST` | `/` | Create a new key. **The raw key is returned exactly once** — only its hash is stored. |
| `GET` | `/` | List the current user's keys (metadata only, never the raw secret). |
| `DELETE` | `/{key_id}` | Revoke a key. |

### Health

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | Liveness check — `{"status": "ok", "service": "Jury API"}`. |

---

## Authentication

Jury supports two credential types over the **same** header, so the SDK and the browser frontend share one auth path:

```
Authorization: Bearer <token>
```

- **JWT** — issued by `/api/auth/login`, used by the frontend session. Identifies the user via a `sub` claim (user ID).
- **API key** — prefixed `jk_`, generated via `/api/api-keys`, used by the SDK and other programmatic clients.

`get_current_user` tells them apart by the `jk_` prefix (JWTs always start with `ey`, the base64url encoding of `{"`), then branches to JWT decoding or a SHA-256 hash lookup accordingly. This means:

- Every route only has to depend on one function regardless of credential type.
- API keys don't expire and aren't tied to a login session, which JWTs can't offer — the two credential types solve genuinely different problems rather than being redundant.

The daily check quota (`DAILY_CHECK_LIMIT`, see below) is enforced **per user**, not per credential — so creating more API keys doesn't grant more quota.

---

## Security

- **No default secrets.** The app raises a `RuntimeError` on startup if `SECRET_KEY` is missing, rather than silently signing tokens with a value visible in source control.
- **Password strength validation** at the schema layer (`UserCreate`): minimum length plus upper/lower/digit/special-character requirements.
- **Brute-force login protection.** Failed attempts are tracked per-user; 5 failures locks the account for 15 minutes. Naive UTC datetimes are used deliberately throughout this logic, since SQLite drops timezone info on round-trip and comparing aware vs. naive datetimes raises a `TypeError`.
- **API keys are never stored in retrievable form.** Only a SHA-256 hash and a short, non-sensitive display prefix (e.g. `jk_AbCdEfGh...`) are persisted. The raw key is shown once, at creation, and cannot be recovered afterward.
- **Correct error semantics on malformed tokens.** A JWT with a non-numeric or missing `sub` claim returns `401 Unauthorized` instead of an unhandled `500`.
- **Per-owner uniqueness constraints** at the database level (`UniqueConstraint`) for policy names per user and rule names per policy — not just app-level checks.
- **CORS** is explicitly allow-listed via `ALLOWED_ORIGINS`, not left open.

---

## Project structure

```
backend/
├── main.py                  # App entrypoint, CORS, router registration
├── Dockerfile
├── requirements.txt
├── models/
│   ├── database.py          # Engine, session factory, Base, get_db()
│   └── models.py            # User, Policy, Rule, Content, ApiKey ORM models
├── routes/
│   ├── auth.py               # Signup / login
│   ├── policies.py           # Policy CRUD
│   ├── rules.py               # Rule CRUD, nested under a policy
│   ├── contents.py           # Content submission + verdict retrieval
│   └── api_keys.py           # API key lifecycle
├── schemas/
│   └── schemas.py            # Pydantic request/response models
├── utils/
│   ├── auth.py               # Password hashing, JWT, lockout, get_current_user
│   ├── api_keys.py           # Key generation, hashing, authentication
│   └── quota.py              # Daily check limit enforcement
└── core/
    ├── llm.py                # Groq/ChatGroq client construction
    ├── prompt.py             # Moderation prompt template + rule formatting
    └── chain.py               # LangChain chain assembly + JSON response parsing
```

---

## Running locally

**1. Clone and install:**

```bash
git clone https://github.com/MohamedFarouk94/jury.git
cd jury/backend
pip install -r requirements.txt
```

**2. Configure environment.** Create a `.env` in `backend/`:

```env
GROQ_API_KEY=your_groq_api_key_here
SECRET_KEY=your_jwt_secret_key_here
DATABASE_URL=sqlite:///./jury.db
ALLOWED_ORIGINS=http://localhost:5500,http://127.0.0.1:5500,https://your-vercel-app.vercel.app
EXEMPT_USERS=comma,separated,usernames
```

- `SECRET_KEY` — required; the app refuses to start without it.
- `EXEMPT_USERS` — usernames that bypass the daily check quota entirely.

**3. Run:**

```bash
uvicorn main:app --reload --port 7860
```

The API will be live at `http://localhost:7860`, with interactive docs at `http://localhost:7860/docs`.

### Persistence on Hugging Face Spaces

Space containers have an ephemeral filesystem — anything written to disk is lost on restart or redeploy. In production, `DATABASE_URL` points at a Hugging Face **Storage Bucket** mounted at `/data`, configured entirely through Space settings and secrets rather than in application code, so `jury.db` survives restarts. Locally, the same `DATABASE_URL` env var just points at a file in the working directory — no code branches on which environment it's running in.

**4. (Optional) Run the frontend against it:**

```bash
cd ../frontend
python3 -m http.server 5500
```

---

## Notable engineering decisions

- **`policy.check(content)`, not `content.check(policy)`.** The policy owns the rules that drive evaluation logic, so it's the natural object to own the `check` method — `Content` stays a simple data object. This principle carries through from the SDK design into the API shape itself.
- **Rule indices, not just IDs.** Rules within a policy carry a `policy_rule_index` (1-based, contiguous) separate from their database `id`. This gives the LLM stable, human-readable rule identifiers (`rule_1`, `rule_2`...) independent of database internals, and lets rules be deleted without leaving gaps.
- **Verdicts run as background tasks.** Content submission returns immediately rather than blocking on an LLM round-trip, at the cost of the client needing to poll for the completed verdict.
- **JWTs and API keys share one auth dependency.** Rather than maintaining two parallel auth stacks, both credential types resolve through `get_current_user` via a single header, differentiated by a fixed prefix.
- **Quota is per-user, not per-credential**, closing an obvious loophole where a user could mint unlimited API keys to bypass rate limiting.

---

## Tech stack

**Backend:** FastAPI · SQLAlchemy · SQLite · `python-jose` (JWT) · `passlib`/bcrypt · LangChain · Groq (`llama-3.3-70b-versatile`)
**Frontend:** Vanilla JavaScript (ES modules), no framework, no bundler
**SDK:** `httpx` (sync), `rich` for pretty-printing
**Infrastructure:** Docker on Hugging Face Spaces · Vercel (frontend)