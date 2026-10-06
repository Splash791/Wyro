def test_dev_user_fixture_persists(session, dev_user):
    from app.models import User

    found = session.get(User, dev_user.id)
    assert found is not None
    assert found.email == "dev@wyro.app"
