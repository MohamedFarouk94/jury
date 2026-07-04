from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from models.database import get_db
from models.models import ApiKey, User
from schemas.schemas import ApiKeyCreate, ApiKeyOut, ApiKeyCreatedOut
from utils.auth import get_current_user
from utils.api_keys import generate_api_key

router = APIRouter(prefix="/api-keys", tags=["API Keys"])


@router.post("/", response_model=ApiKeyCreatedOut, status_code=status.HTTP_201_CREATED)
def create_api_key(
    payload: ApiKeyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a new API key for programmatic (SDK) access. The full key is
    returned exactly once, in this response — only its hash and a display
    prefix are stored, so it can never be retrieved again after this call.
    Users may create as many keys as they like: the daily check quota is
    enforced per-user, not per-key, so extra keys don't grant extra quota.
    """
    raw_key, display_prefix, hashed_key = generate_api_key()

    api_key = ApiKey(
        user_id=current_user.id,
        name=payload.name,
        prefix=display_prefix,
        hashed_key=hashed_key,
    )
    db.add(api_key)
    db.commit()
    db.refresh(api_key)

    return {
        "id": api_key.id,
        "name": api_key.name,
        "prefix": api_key.prefix,
        "created_at": api_key.created_at,
        "last_used_at": api_key.last_used_at,
        "revoked": api_key.revoked,
        "key": raw_key,
    }


@router.get("/", response_model=list[ApiKeyOut])
def list_api_keys(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return db.query(ApiKey).filter(ApiKey.user_id == current_user.id).all()


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_api_key(
    key_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    api_key = db.query(ApiKey).filter(ApiKey.id == key_id, ApiKey.user_id == current_user.id).first()
    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found.")

    api_key.revoked = True
    api_key.revoked_at = datetime.now(timezone.utc)
    db.commit()