import pytest
from fastapi import HTTPException

from app.auth import DEV_USER_ID, get_current_user
from app.seed import seed_dev_user


def test_seed_is_idempotent(session):
    u1 = seed_dev_user(session)
    u2 = seed_dev_user(session)
    assert u1.id == u2.id == DEV_USER_ID


def test_valid_token_returns_dev_user(session):
    seed_dev_user(session)
    user = get_current_user(authorization="Bearer dev-token", session=session)
    assert user.id == DEV_USER_ID


def test_bad_token_rejected(session):
    seed_dev_user(session)
    with pytest.raises(HTTPException) as exc:
        get_current_user(authorization="Bearer nope", session=session)
    assert exc.value.status_code == 401
