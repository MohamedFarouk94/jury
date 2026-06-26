from pydantic import BaseModel, EmailStr
from typing import Optional, Any
from datetime import datetime


# ── Auth ────────────────────────────────────────────────────────────────────

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: int
    username: str
    email: str
    created_at: datetime

    model_config = {"from_attributes": True}


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    username: str
    password: str


# ── Rules ───────────────────────────────────────────────────────────────────

class RuleCreate(BaseModel):
    name: str
    description: str


class RuleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class RuleOut(BaseModel):
    id: int
    name: str
    description: str
    policy_id: int
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Policies ─────────────────────────────────────────────────────────────────

class PolicyCreate(BaseModel):
    name: str
    description: Optional[str] = None


class PolicyOut(BaseModel):
    id: int
    name: str
    description: Optional[str]
    owner_id: int
    created_at: datetime
    rules: list[RuleOut] = []

    model_config = {"from_attributes": True}


class PolicySummary(BaseModel):
    id: int
    name: str
    description: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Content ──────────────────────────────────────────────────────────────────

class ContentCreate(BaseModel):
    text: str
    policy_id: int


class ContentOut(BaseModel):
    id: int
    text: str
    policy_id: int
    verdict: Optional[Any] = None  # parsed JSON or None
    created_at: datetime

    model_config = {"from_attributes": True}
