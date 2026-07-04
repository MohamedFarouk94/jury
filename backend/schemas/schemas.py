import re
from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional, Any
from datetime import datetime


# ── Auth ────────────────────────────────────────────────────────────────────

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, value: str) -> str:
        if len(value) < 8:
            raise ValueError("Password must be at least 8 characters long.")
        if not re.search(r"[A-Z]", value):
            raise ValueError("Password must contain at least one uppercase letter.")
        if not re.search(r"[a-z]", value):
            raise ValueError("Password must contain at least one lowercase letter.")
        if not re.search(r"\d", value):
            raise ValueError("Password must contain at least one digit.")
        if not re.search(r"[^A-Za-z0-9]", value):
            raise ValueError("Password must contain at least one special character.")
        return value


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


# ── API Keys ─────────────────────────────────────────────────────────────────

class ApiKeyCreate(BaseModel):
    name: Optional[str] = None


class ApiKeyOut(BaseModel):
    id: int
    name: Optional[str]
    prefix: str
    created_at: datetime
    last_used_at: Optional[datetime]
    revoked: bool

    model_config = {"from_attributes": True}


class ApiKeyCreatedOut(ApiKeyOut):
    key: str  # the raw secret — present only in the create response, shown once


# ── Rules ───────────────────────────────────────────────────────────────────

class RuleCreate(BaseModel):
    name: str
    description: str


class RuleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class RuleOut(BaseModel):
    id: int
    policy_rule_index: int
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