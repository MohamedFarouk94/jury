from sqlalchemy import Column, Integer, String, ForeignKey, Text, DateTime, Date, Boolean, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime, timezone

from .database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Daily check quota tracking
    checks_date = Column(Date, nullable=True)   # The date the counter was last reset
    checks_count = Column(Integer, default=0)   # How many checks used today

    # Brute-force login protection
    failed_login_attempts = Column(Integer, default=0, nullable=False)
    lockout_until = Column(DateTime, nullable=True)  # naive UTC; set when locked out

    policies = relationship("Policy", back_populates="owner", cascade="all, delete-orphan")
    api_keys = relationship("ApiKey", back_populates="user", cascade="all, delete-orphan")


class Policy(Base):
    __tablename__ = "policies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Policy name must be unique per owner (mirrors rule-name-per-policy below)
    __table_args__ = (
        UniqueConstraint("owner_id", "name", name="uq_policy_name_per_owner"),
    )

    owner = relationship("User", back_populates="policies")
    rules = relationship("Rule", back_populates="policy", cascade="all, delete-orphan", order_by="Rule.policy_rule_index")
    contents = relationship("Content", back_populates="policy", cascade="all, delete-orphan")


class Rule(Base):
    __tablename__ = "rules"

    id = Column(Integer, primary_key=True, index=True)
    policy_rule_index = Column(Integer, nullable=False)  # 1-based index within the policy
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)
    policy_id = Column(Integer, ForeignKey("policies.id"), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Rule name must be unique within a policy
    __table_args__ = (
        UniqueConstraint("policy_id", "name", name="uq_rule_name_per_policy"),
    )

    policy = relationship("Policy", back_populates="rules")


class Content(Base):
    __tablename__ = "contents"

    id = Column(Integer, primary_key=True, index=True)
    text = Column(Text, nullable=False)
    policy_id = Column(Integer, ForeignKey("policies.id"), nullable=False)
    verdict = Column(Text, nullable=True)  # Stored as JSON string; null while pending
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    policy = relationship("Policy", back_populates="contents")


class ApiKey(Base):
    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(100), nullable=True)  # optional user-facing label, e.g. "CI pipeline"

    # Only a short, non-sensitive slice of the raw key is stored in the clear,
    # for display purposes (e.g. "jk_AbCdEfGh..."). The actual secret is never stored.
    prefix = Column(String(16), nullable=False, index=True)

    # SHA-256 hex digest of the full raw key. Looked up directly on auth.
    hashed_key = Column(String(64), unique=True, index=True, nullable=False)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_used_at = Column(DateTime, nullable=True)

    revoked = Column(Boolean, default=False, nullable=False)
    revoked_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="api_keys")