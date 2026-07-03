# Jury — AI-Powered Content Moderation

Jury is a full-stack admin tool for moderating social media content using AI. Admins define **policies** made up of **rules**, submit **content** for review, and an LLM (via Groq) returns a structured verdict against each rule. A web dashboard surfaces those verdicts for human review, and a Python SDK / CLI give programmatic access to the same backend.

---

## Live

- **Dashboard:** [jury-livid.vercel.app](https://jury-livid.vercel.app)
- **API:** `https://mfarouk-jury-backend.hf.space` (routes under `/api`)
- **API docs (Swagger):** `https://mfarouk-jury-backend.hf.space/docs`

---

## How it fits together

```
                 ┌──────────────┐
                 │   Backend    │  FastAPI · SQLAlchemy · Groq LLM
                 │ (HF Spaces)  │  auth, policies, rules, content, verdicts
                 └──────┬───────┘
                        │  REST API (/api)
        ┌───────────────┼───────────────┬───────────────┐
        │               │               │               │
 ┌─────────────┐  ┌────────────┐  ┌───────────┐   ┌────────────┐
 │  Frontend   │  │    SDK     │  │    CLI    │   │  (future)  │
 │  (Vercel)   │  │  (Python)  │  │           │   │  clients   │
 │  Vanilla JS │  │            │  │           │   │            │
 └─────────────┘  └────────────┘  └───────────┘   └────────────┘
```

The **backend** is the single source of truth — everything else is a client of its API. The **frontend** is the human-facing admin dashboard. The **SDK** wraps the API for use in other Python projects/scripts. The **CLI** (built on top of the SDK) is for terminal/scripted workflows — exact scope still TBD.

---

## Repo layout

```
jury/
├── README.md              ← you are here
├── backend/                ← FastAPI app — see backend/README.md
├── frontend/                ← Vanilla JS SPA — see frontend/README.md
├── sdk/                    ← Python SDK — see sdk/README.md
└── cli/                    ← CLI — see cli/README.md
```

| Part       | Status      | Stack                                      | Docs                            |
|------------|-------------|---------------------------------------------|----------------------------------|
| `backend/` | Deployed    | FastAPI, SQLAlchemy, SQLite, LangChain, Groq | [backend/README.md](backend/README.md)   |
| `frontend/`| Deployed    | Vanilla JS (ES modules), HTML/CSS            | [frontend/README.md](frontend/README.md) |
| `sdk/`     | Planned     | Python                                       | [sdk/README.md](sdk/README.md)           |
| `cli/`     | Planned     | TBD                                          | [cli/README.md](cli/README.md)           |

> Note: `backend/README.md` also doubles as the Hugging Face Space card — its YAML frontmatter configures how the Space renders on Hugging Face, in addition to documenting local backend setup.

---

## Quickstart (local dev)

Each part has its own setup instructions in its README. At a high level:

```bash
# Backend
cd backend && python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.template.txt .env   # fill in GROQ_API_KEY, SECRET_KEY
uvicorn main:app --reload --port 8000

# Frontend (separate terminal)
cd frontend
python3 -m http.server 5500   # ensure config.js points at http://localhost:8000
```

See [backend/README.md](backend/README.md) and [frontend/README.md](frontend/README.md) for full details, and [sdk/README.md](sdk/README.md) / [cli/README.md](cli/README.md) once those are built out.

---

## Core concepts

| Concept   | Description |
|-----------|-------------|
| **Policy**  | A named collection of moderation rules (e.g. "Community Guidelines") |
| **Rule**    | A single condition a policy checks for (e.g. "no hate speech") |
| **Content** | A piece of submitted text/media to be evaluated against a policy |
| **Verdict** | Per-rule LLM judgment on a piece of content: `0` (no violation), `1` (possible violation), `2` (clear violation) |

### Verdict color logic (dashboard)

| Color     | Condition |
|-----------|-----------|
| ⬜ Pending | Verdict not yet returned by LLM |
| 🟣 Purple  | Error happened in moderation chain | 
| 🟢 Green   | All rules returned `0` |
| 🟡 Yellow  | No rule returned `2`, but ≥1 returned `1` |
| 🔴 Red     | At least one rule returned `2` |

---

## Roadmap

- [ ] Verify Hugging Face Spaces persistent storage is enabled (SQLite currently resets on container rebuild)
- [ ] Richer admin stats (daily check usage, most active users)
- [ ] Python SDK for programmatic access to the API
- [ ] CLI (scope TBD)
- [ ] Possible migration off SQLite to an external database