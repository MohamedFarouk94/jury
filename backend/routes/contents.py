import json
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from sqlalchemy.orm import Session

from models.database import get_db
from models.models import Content, Policy, Rule, User
from schemas.schemas import ContentCreate, ContentOut
from utils.auth import get_current_user
from utils.quota import check_and_increment_quota
from core.chain import run_moderation_chain

router = APIRouter(prefix="/contents", tags=["Contents"])


def _run_verdict(content_id: int, rules: list[dict], text: str, db: Session):
    """Background task: run the LLM chain and persist the verdict."""
    try:
        verdict = run_moderation_chain(rules, text)
    except Exception as e:
        verdict = {"error": str(e), "details": "Moderation chain failed."}

    content = db.query(Content).filter(Content.id == content_id).first()
    if content:
        content.verdict = json.dumps(verdict)
        db.commit()
    db.close()


def _serialize(content: Content) -> dict:
    return {
        "id": content.id,
        "text": content.text,
        "policy_id": content.policy_id,
        "verdict": json.loads(content.verdict) if content.verdict else None,
        "created_at": content.created_at,
    }


@router.post("/", response_model=ContentOut, status_code=status.HTTP_201_CREATED)
def check_content(
    payload: ContentCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    policy = db.query(Policy).filter(
        Policy.id == payload.policy_id,
        Policy.owner_id == current_user.id,
    ).first()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found.")

    rules = (
        db.query(Rule)
        .filter(Rule.policy_id == policy.id)
        .order_by(Rule.policy_rule_index)
        .all()
    )
    if not rules:
        raise HTTPException(status_code=400, detail="This policy has no rules yet. Add at least one rule before checking content.")

    # Enforce daily quota (exempt users bypass this)
    check_and_increment_quota(current_user, db)

    content = Content(text=payload.text, policy_id=policy.id)
    db.add(content)
    db.commit()
    db.refresh(content)

    # Use policy_rule_index as the rule id sent to the LLM
    rules_data = [
        {
            "id": str(r.policy_rule_index),
            "name": r.name,
            "description": r.description,
        }
        for r in rules
    ]

    from models.database import SessionLocal
    bg_db = SessionLocal()
    background_tasks.add_task(_run_verdict, content.id, rules_data, content.text, bg_db)

    return _serialize(content)


@router.get("/policy/{policy_id}", response_model=list[ContentOut])
def list_contents(
    policy_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    policy = db.query(Policy).filter(
        Policy.id == policy_id,
        Policy.owner_id == current_user.id,
    ).first()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found.")

    contents = (
        db.query(Content)
        .filter(Content.policy_id == policy_id)
        .order_by(Content.created_at.asc())
        .all()
    )
    return [_serialize(c) for c in contents]


@router.get("/{content_id}", response_model=ContentOut)
def get_content(
    content_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    content = db.query(Content).join(Policy).filter(
        Content.id == content_id,
        Policy.owner_id == current_user.id,
    ).first()
    if not content:
        raise HTTPException(status_code=404, detail="Content not found.")
    return _serialize(content)
