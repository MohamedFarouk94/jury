from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os

load_dotenv()

from models.database import engine
from models import Base

# Import all models so SQLAlchemy registers them before create_all
from models.models import User, Policy, Rule, Content  # noqa: F401

Base.metadata.create_all(bind=engine)

from routes import auth_router, policies_router, rules_router, contents_router

app = FastAPI(
    title="Jury API",
    description="AI-powered social media content moderation backend.",
    version="1.0.0",
)

# ── CORS ──────────────────────────────────────────────────────────────────────
raw_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:5500,http://127.0.0.1:5500")
allowed_origins = [o.strip() for o in raw_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(auth_router)
app.include_router(policies_router)
app.include_router(rules_router)
app.include_router(contents_router)


@app.get("/", tags=["Health"])
def health_check():
    return {"status": "ok", "service": "Jury API"}
