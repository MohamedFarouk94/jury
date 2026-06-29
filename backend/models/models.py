from sqlalchemy import Column, Integer, String, ForeignKey, Text, DateTime, Date, UniqueConstraint
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

    policies = relationship("Policy", back_populates="owner", cascade="all, delete-orphan")


class Policy(Base):
    __tablename__ = "policies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

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
