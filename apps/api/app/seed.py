import uuid

from sqlalchemy.orm import Session

from app.models import User

DEV_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


def seed_dev_user(session: Session) -> User:
    user = session.get(User, DEV_USER_ID)
    if user is None:
        user = User(id=DEV_USER_ID, email="dev@wyro.app", auth_provider="dev")
        session.add(user)
        session.flush()
    return user
