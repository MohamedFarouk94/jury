from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from models.database import get_db
from models.models import Policy, User
from schemas.schemas import PolicyCreate, PolicyOut, PolicySummary
from utils.auth import get_current_user

router = APIRouter(prefix="/policies", tags=["Policies"])


def check_policy_name_conflict(owner_id: int, name: str, db: Session, exclude_policy_id: int = None):
    """Raise 409 if this owner already has a policy with this name."""
    query = db.query(Policy).filter(Policy.owner_id == owner_id, Policy.name == name)
    if exclude_policy_id:
        query = query.filter(Policy.id != exclude_policy_id)
    if query.first():
        raise HTTPException(
            status_code=409,
            detail=f"You already have a policy named '{name}'."
        )


@router.post("/", response_model=PolicyOut, status_code=status.HTTP_201_CREATED)
def create_policy(
    payload: PolicyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    check_policy_name_conflict(current_user.id, payload.name, db)

    policy = Policy(
        name=payload.name,
        description=payload.description,
        owner_id=current_user.id,
    )
    db.add(policy)
    db.commit()
    db.refresh(policy)
    return policy


@router.get("/", response_model=list[PolicySummary])
def list_policies(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return db.query(Policy).filter(Policy.owner_id == current_user.id).all()


@router.get("/{policy_id}", response_model=PolicyOut)
def get_policy(
    policy_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    policy = db.query(Policy).filter(Policy.id == policy_id, Policy.owner_id == current_user.id).first()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found.")
    return policy


@router.delete("/{policy_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_policy(
    policy_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    policy = db.query(Policy).filter(Policy.id == policy_id, Policy.owner_id == current_user.id).first()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found.")
    db.delete(policy)
    db.commit()
