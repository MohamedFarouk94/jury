from datetime import datetime, timedelta, timezone
from passlib.context import CryptContext
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from dotenv import load_dotenv
import os

from models.database import get_db
from models.models import User
from utils.api_keys import is_api_key, authenticate_api_key

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    # Never fall back to a hardcoded default here — that would silently sign
    # every token with a value an attacker can find in this source file.
    raise RuntimeError(
        "SECRET_KEY environment variable is not set. Refusing to start: set "
        "SECRET_KEY in your .env file (local) or Space secrets (deployed) "
        "before running the app."
    )

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 1 week

# ── Brute-force login protection ────────────────────────────────────────────
FAILED_LOGIN_LIMIT = 5
LOCKOUT_DURATION_MINUTES = 15

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(data: dict) -> str:
    payload = data.copy()
    payload["exp"] = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


# ── Login lockout helpers ────────────────────────────────────────────────────
# Uses naive UTC datetimes throughout (datetime.utcnow) rather than
# timezone-aware ones, since SQLite drops tzinfo on round-trip and mixing
# aware/naive datetimes in a comparison raises a TypeError.

def is_locked_out(user: User) -> bool:
    """Whether this account is currently locked out from repeated failed logins."""
    return bool(user.lockout_until and user.lockout_until > datetime.utcnow())


def register_failed_login(user: User, db: Session) -> None:
    """Increment the failed-attempt counter; lock the account if the limit is hit."""
    user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
    if user.failed_login_attempts >= FAILED_LOGIN_LIMIT:
        user.lockout_until = datetime.utcnow() + timedelta(minutes=LOCKOUT_DURATION_MINUTES)
        user.failed_login_attempts = 0
    db.commit()


def reset_login_attempts(user: User, db: Session) -> None:
    """Clear failed-attempt tracking after a successful login."""
    if user.failed_login_attempts or user.lockout_until:
        user.failed_login_attempts = 0
        user.lockout_until = None
        db.commit()


# ── Current-user resolution (JWT or API key) ────────────────────────────────

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # SDK/programmatic clients send an API key through the exact same
    # "Authorization: Bearer <token>" header as a JWT. We tell them apart by
    # the fixed "jk_" prefix and branch accordingly.
    if is_api_key(token):
        return authenticate_api_key(token, db)

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        raw_user_id = payload.get("sub")
        if raw_user_id is None:
            raise credentials_exception
        user_id = int(raw_user_id)
    except (JWTError, ValueError, TypeError):
        # ValueError/TypeError catches a non-numeric "sub" claim (e.g. a
        # forged or corrupted token) so it correctly returns 401 instead of
        # crashing into an unhandled 500.
        raise credentials_exception

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception
    return user
