from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_session
from app.models import User
from app.seed import DEV_USER_ID


def get_current_user(
    authorization: str = Header(default=""),
    session: Session = Depends(get_session),
) -> User:
    expected = f"Bearer {settings.dev_token}"
    if authorization != expected:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    user = session.get(User, DEV_USER_ID)
    if user is None:
        raise HTTPException(status_code=401, detail="Dev user not seeded")
    return user
