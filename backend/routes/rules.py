from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from models.database import get_db
from models.models import Policy, Rule, User
from schemas.schemas import RuleCreate, RuleUpdate, RuleOut
from utils.auth import get_current_user

router = APIRouter(prefix="/policies/{policy_id}/rules", tags=["Rules"])


def get_owned_policy(policy_id: int, db: Session, user: User) -> Policy:
    policy = db.query(Policy).filter(Policy.id == policy_id, Policy.owner_id == user.id).first()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found.")
    return policy


def check_name_conflict(policy_id: int, name: str, db: Session, exclude_rule_id: int = None):
    """Raise 409 if a rule with this name already exists in the policy."""
    query = db.query(Rule).filter(Rule.policy_id == policy_id, Rule.name == name)
    if exclude_rule_id:
        query = query.filter(Rule.id != exclude_rule_id)
    if query.first():
        raise HTTPException(
            status_code=409,
            detail=f"A rule named '{name}' already exists in this policy."
        )


def next_policy_rule_index(policy_id: int, db: Session) -> int:
    """Return the next available 1-based index for a rule within a policy."""
    max_index = db.query(Rule).filter(Rule.policy_id == policy_id).count()
    return max_index + 1


@router.post("/", response_model=RuleOut, status_code=status.HTTP_201_CREATED)
def add_rule(
    policy_id: int,
    payload: RuleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    get_owned_policy(policy_id, db, current_user)
    check_name_conflict(policy_id, payload.name, db)

    rule = Rule(
        name=payload.name,
        description=payload.description,
        policy_id=policy_id,
        policy_rule_index=next_policy_rule_index(policy_id, db),
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


@router.put("/{rule_id}", response_model=RuleOut)
def edit_rule(
    policy_id: int,
    rule_id: int,
    payload: RuleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    get_owned_policy(policy_id, db, current_user)
    rule = db.query(Rule).filter(Rule.id == rule_id, Rule.policy_id == policy_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found.")

    if payload.name is not None and payload.name != rule.name:
        check_name_conflict(policy_id, payload.name, db, exclude_rule_id=rule_id)
        rule.name = payload.name
    if payload.description is not None:
        rule.description = payload.description

    db.commit()
    db.refresh(rule)
    return rule


@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_rule(
    policy_id: int,
    rule_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    get_owned_policy(policy_id, db, current_user)
    rule = db.query(Rule).filter(Rule.id == rule_id, Rule.policy_id == policy_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found.")

    deleted_index = rule.policy_rule_index
    db.delete(rule)

    # Re-sequence remaining rules so indices stay contiguous
    remaining = (
        db.query(Rule)
        .filter(Rule.policy_id == policy_id, Rule.policy_rule_index > deleted_index)
        .order_by(Rule.policy_rule_index)
        .all()
    )
    for r in remaining:
        r.policy_rule_index -= 1

    db.commit()
