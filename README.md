# Jury — AI-Powered Content Moderation

Jury is a full-stack admin tool for moderating social media content using AI. Users create policies with rules, then submit content to be evaluated by an LLM (via Groq) which returns a structured verdict per rule.

---

## Project Structure

```
jury/
├── .gitignore
├── README.md
├── backend/
│   ├── .env.template.txt       ← Copy and rename to .env
│   ├── requirements.txt
│   ├── main.py                 ← FastAPI app entry point
│   ├── core/
│   │   ├── __init__.py
│   │   ├── llm.py              ← Groq LLM setup
│   │   ├── prompt.py           ← Prompt template
│   │   └── chain.py            ← LangChain moderation chain
│   ├── models/
│   │   ├── __init__.py
│   │   ├── database.py         ← SQLAlchemy engine & session
│   │   └── models.py           ← User, Policy, Rule, Content
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   ├── policies.py
│   │   ├── rules.py
│   │   └── contents.py
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── schemas.py          ← Pydantic request/response models
│   └── utils/
│       ├── __init__.py
│       └── auth.py             ← JWT & password utilities
└── frontend/
    ├── index.html
    ├── app.js                  ← Entry point
    ├── config.js               ← Set JURY_API_URL here
    ├── vercel.json
    ├── styles/
    │   └── main.css
    ├── services/
    │   └── api.js              ← All fetch calls to the backend
    ├── utils/
    │   └── verdict.js          ← Verdict color logic
    ├── pages/
    │   └── Dashboard.js        ← Main authenticated view
    └── components/
        ├── auth/
        │   └── AuthPage.js
        ├── policies/
        │   ├── PoliciesSidebar.js
        │   └── RulesPanel.js
        └── content/
            └── ContentFeed.js
```

---

## Backend Setup (Local)

```bash
cd backend

# 1. Create and activate virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Create your .env file
cp .env.template.txt .env
# Edit .env and fill in GROQ_API_KEY and SECRET_KEY

# 4. Run the server
uvicorn main:app --reload --port 8000
```

API docs available at: http://localhost:8000/docs

---

## Frontend Setup (Local)

The frontend is plain HTML/JS — no build step needed.

Open `frontend/index.html` with a local server (e.g. VS Code Live Server, or):

```bash
cd frontend
python -m http.server 5500
```

Then open http://localhost:5500

Make sure `config.js` has `JURY_API_URL = "http://localhost:8000"` for local dev.

---

## Deployment

### Backend → Hugging Face Spaces

1. Create a new Space with the **FastAPI** template (Docker or Python SDK).
2. Upload the contents of the `backend/` folder.
3. Set the following **Secrets** in the Space settings:
   - `GROQ_API_KEY`
   - `SECRET_KEY`
   - `ALLOWED_ORIGINS` → comma-separated list including your Vercel URL, e.g. `https://your-app.vercel.app`

### Frontend → Vercel

1. Push the `frontend/` folder to a GitHub repository.
2. Import the repo in Vercel. Set the root directory to `frontend/`.
3. Before deploying, update `config.js`:
   ```js
   window.JURY_API_URL = "https://your-hf-space.hf.space";
   ```
4. Deploy — `vercel.json` handles SPA routing automatically.

---

## Environment Variables

| Variable         | Required | Description                                      |
|------------------|----------|--------------------------------------------------|
| `GROQ_API_KEY`   | Yes      | Your Groq API key (https://console.groq.com)    |
| `SECRET_KEY`     | Yes      | Random string for JWT signing                   |
| `DATABASE_URL`   | No       | Defaults to `sqlite:///./jury.db`               |
| `ALLOWED_ORIGINS`| No       | Comma-separated CORS origins (default: localhost)|

---

## Verdict Color Logic

| Color  | Condition |
|--------|-----------|
| ⬜ Pending | Verdict not yet returned by LLM |
| 🟢 Green  | All rules returned 0 (no violation) |
| 🟡 Yellow | No rule returned 2, but ≥1 returned 1 (possible violation) |
| 🔴 Red    | At least one rule returned 2 (clear violation) |
