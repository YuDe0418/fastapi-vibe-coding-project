import pytest
from fastapi.testclient import TestClient
from app.main import create_app
from app.core.config import Settings
from app.models.entities import User
from app.core.security import hash_password

PASSWORD="safe-password-123"

@pytest.fixture
def app(tmp_path):
    return create_app(Settings(secret_key="test-only-"+"x"*48, database_url=f"sqlite:///{tmp_path / 'test.db'}", _env_file=None))

@pytest.fixture
def client(app):
    with TestClient(app) as client:
        yield client

@pytest.fixture
def member(client):
    data={"username":"alice","nickname":"小明","email":"alice@example.com","password":PASSWORD}
    assert client.post("/users/register",json=data).status_code==201
    assert client.post("/users/login",json={"username":"alice","password":PASSWORD}).status_code==200
    return client.get("/users/me").json()

@pytest.fixture
def admin(app,client):
    with app.state.session_factory() as db:
        user=User(username="admin",nickname="管理員",email="admin@example.com",hashed_password=hash_password(PASSWORD),is_admin=True)
        db.add(user);db.commit()
    assert client.post("/users/login",json={"username":"admin","password":PASSWORD}).status_code==200
    return client.get("/users/me").json()
