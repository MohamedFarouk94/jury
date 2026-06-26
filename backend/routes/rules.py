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


@router.post("/", response_model=RuleOut, status_code=status.HTTP_201_CREATED)
def add_rule(
    policy_id: int,
    payload: RuleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    get_owned_policy(policy_id, db, current_user)
    rule = Rule(name=payload.name, description=payload.description, policy_id=policy_id)
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

    if payload.name is not None:
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
    db.delete(rule)
    db.commit()
