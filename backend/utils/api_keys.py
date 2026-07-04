import hashlib
import secrets
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from models.models import ApiKey, User

# Fixed prefix so a token can be identified as an API key at a glance and
# routed differently from a JWT (JWTs always start with "ey", the base64url
# encoding of '{"'). This lets API keys and JWTs share the same
# "Authorization: Bearer <token>" header and the same get_current_user dependency.
API_KEY_PREFIX = "jk_"

# How much of the raw key is safe to store/display in the clear so a user can
# recognize a key in a list later (e.g. "jk_AbCdEfGh..."). Not enough entropy
# on its own to be guessable, so this is not sensitive.
DISPLAY_PREFIX_LENGTH = 12


def generate_api_key() -> tuple[str, str, str]:
    """
    Generate a brand-new API key.

    Returns (raw_key, display_prefix, hashed_key):
    - raw_key: the full secret. Shown to the user exactly ONCE (at creation
      time) and never stored or retrievable again.
    - display_prefix: short, non-sensitive slice used to identify the key
      later in a "your API keys" list.
    - hashed_key: what actually gets persisted to the database.
    """
    raw_key = f"{API_KEY_PREFIX}{secrets.token_urlsafe(32)}"
    display_prefix = raw_key[:DISPLAY_PREFIX_LENGTH]
    hashed_key = hash_api_key(raw_key)
    return raw_key, display_prefix, hashed_key


def hash_api_key(raw_key: str) -> str:
    """
    API keys are high-entropy random strings (unlike user-chosen passwords),
    so a fast deterministic hash (SHA-256) is the appropriate tool here — it
    lets us look a key up directly by its hash instead of needing bcrypt's
    slow, salted comparison against every stored key.
    """
    return hashlib.sha256(raw_key.encode()).hexdigest()


def is_api_key(token: str) -> bool:
    return token.startswith(API_KEY_PREFIX)


def authenticate_api_key(token: str, db: Session) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or revoked API key.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    hashed = hash_api_key(token)
    api_key = db.query(ApiKey).filter(ApiKey.hashed_key == hashed).first()

    if not api_key or api_key.revoked:
        raise credentials_exception

    user = db.query(User).filter(User.id == api_key.user_id).first()
    if not user:
        raise credentials_exception

    api_key.last_used_at = datetime.now(timezone.utc)
    db.commit()

    return user