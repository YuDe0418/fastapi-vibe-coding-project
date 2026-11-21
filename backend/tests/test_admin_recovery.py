import pytest
from sqlalchemy import select
from app.core.reset_admin import reset_admin
from app.models.entities import User, AuditLog
from app.core.security import verify_password
from conftest import PASSWORD


def test_admin_recovery_revokes_sessions(client, app, admin):
    old_cookie = client.cookies.get("board_session")
    new_password = "new-admin-password-789"
    reset_admin(app.state.settings, "ADMIN", new_password)
    assert client.get("/users/me", headers={"Authorization": "Bearer " + old_cookie}).status_code == 401
    assert client.post("/users/login", json={"username": "admin", "password": PASSWORD}).status_code == 401
    response = client.post("/users/login", json={"username": "admin", "password": new_password})
    assert response.status_code == 200
    assert response.json()["is_admin"] is True
    assert response.json()["must_change_password"] is False
    with app.state.session_factory() as db:
        assert db.scalar(select(AuditLog)).action == "reset_admin_password_cli"


def test_recovery_never_promotes_member_or_accepts_weak_password(client, app, member):
    with pytest.raises(ValueError):
        reset_admin(app.state.settings, "alice", "new-admin-password-789")
    with pytest.raises(ValueError):
        reset_admin(app.state.settings, "alice", "short")
    with app.state.session_factory() as db:
        user = db.get(User, member["id"])
        assert user.is_admin is False
        assert verify_password(PASSWORD, user.hashed_password)
        assert db.scalar(select(AuditLog)) is None
