from datetime import date
from fastapi import HTTPException
from sqlalchemy.orm import Session
from dotenv import load_dotenv
import os

load_dotenv()

DAILY_CHECK_LIMIT = int(os.getenv("DAILY_CHECK_LIMIT", "10"))

# Comma-separated usernames in .env that are exempt from the quota
_raw_exempt = os.getenv("EXEMPT_USERS", "")
EXEMPT_USERS: set[str] = {u.strip() for u in _raw_exempt.split(",") if u.strip()}


def check_and_increment_quota(user, db: Session):
    """
    Raises HTTP 429 if the user has hit their daily check limit.
    Exempt users (listed in EXEMPT_USERS env var) are never limited.
    Resets the counter automatically at the start of a new day.
    """
    if user.username in EXEMPT_USERS:
        return

    today = date.today()

    # Reset counter if it's a new day
    if user.checks_date != today:
        user.checks_date = today
        user.checks_count = 0

    if user.checks_count >= DAILY_CHECK_LIMIT:
        raise HTTPException(
            status_code=429,
            detail=f"Daily check limit of {DAILY_CHECK_LIMIT} reached. Try again tomorrow."
        )

    user.checks_count += 1
    db.commit()
