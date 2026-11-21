from datetime import timedelta
import jwt
from fastapi.testclient import TestClient
from sqlalchemy import select
from app.models.entities import User, Post, AuditLog, utcnow
from conftest import PASSWORD


def test_registration_validation_and_no_escalation(client):
    data={"username":"alice","nickname":"小明","email":"alice@example.com","password":PASSWORD}
    rejected=client.post("/users/register",json={**data,"is_admin":True})
    assert rejected.status_code==422
    response=client.post("/api/users/register",json=data)
    assert response.status_code==201
    assert response.json()["is_admin"] is False
    assert "hashed_password" not in response.text
    assert client.post("/users/register",json=data).status_code==409
    assert client.post("/users/register",json={**data,"password":"short"}).status_code==422
    assert client.post("/users/register",json={**data,"password":"密"*30}).status_code==422


def test_login_logout_revocation(client,member):
    token=client.cookies.get("board_session")
    response=client.post("/users/login",json={"username":"alice","password":"incorrect"})
    assert response.status_code==401
    assert client.get("/users/me").status_code==200
    assert client.post("/users/logout").status_code==204
    assert client.get("/users/me").status_code==401
    assert client.get("/users/me",headers={"Authorization":"Bearer "+token}).status_code==401


def test_jwt_expired_and_tampered(client,app,member):
    assert client.get("/users/me",headers={"Authorization":"Bearer invalid"}).status_code==401
    token=jwt.encode({"sub":str(member['id']),"ver":0,"iat":utcnow()-timedelta(hours=2),"exp":utcnow()-timedelta(hours=1),"aud":"common-ground-web","iss":"common-ground"},app.state.settings.secret_key,algorithm="HS256")
    assert client.get("/users/me",headers={"Authorization":"Bearer "+token}).status_code==401


def test_permissions_and_user_updates(client,member):
    post=client.post("/posts",json={"title":"hello","content":"world"}).json()
    assert client.get("/api/admin/users").status_code==403
    assert client.get("/api/admin/stats").status_code==403
    profile={"nickname":"New Name","email":"new@example.com","phone":"123","address":"Taiwan"}
    assert client.put(f"/users/{member['id']}",json=profile).status_code==200
    assert client.put(f"/users/{member['id']}",json={**profile,"is_admin":True}).status_code==422
    client.post("/users/logout")
    client.post("/users/register",json={"username":"bob","nickname":"Bob","email":"bob@example.com","password":PASSWORD})
    client.post("/users/login",json={"username":"bob","password":PASSWORD})
    assert client.put(f"/users/{member['id']}",json=profile).status_code==403
    assert client.delete(f"/users/{member['id']}").status_code==403
    assert client.put(f"/posts/{post['id']}",json={"title":"bad","content":"bad"}).status_code==403
    assert client.delete(f"/posts/{post['id']}").status_code==403
    assert client.put(f"/users/admin/reset-password/{member['id']}",json={"password":"other-password-123"}).status_code==403


def test_crud_replies_search_and_pagination(client,member):
    response=client.post("/api/posts",json={"title":"Python 討論","content":"第一篇","remarks":"補充"})
    assert response.status_code==201
    post=response.json();url=f"/posts/{post['id']}"
    assert post["author_id"]==member["id"]
    assert post["created_at"].endswith("Z") or post["created_at"].endswith("+00:00")
    assert client.get(url).json()["title"]=="Python 討論"
    assert client.put(url,json={"title":"Updated","content":"Hello"}).status_code==200
    reply=client.post(url+"/replies",json={"content":"Nice!"})
    assert reply.status_code==201
    assert client.get(url).json()["reply_count"]==1
    assert client.get("/posts?q=Updated").json()["total"]==1
    assert client.get("/posts?q=missing").json()["total"]==0
    assert client.get("/posts?page=2&page_size=1").json()["items"]==[]
    assert client.get("/posts?page=0").status_code==422
    assert client.get("/posts?sort=popular").status_code==200
    assert client.delete(url).status_code==204
    assert client.get(url).status_code==404


def test_expiration(client,app,member):
    post=client.post("/posts",json={"title":"Expiring","content":"Hello"}).json()
    with app.state.session_factory() as db:
        record=db.get(Post,post["id"]);record.expires_at=utcnow()-timedelta(seconds=1);db.commit()
    assert client.get("/posts").json()["total"]==0
    assert client.get("/posts/mine").json()["total"]==1
    assert client.get(f"/posts/{post['id']}").json()["is_expired"] is True
    assert client.post(f"/posts/{post['id']}/replies",json={"content":"late"}).status_code==409
    assert client.post("/posts",json={"title":"bad","content":"bad","expires_at":"2020-01-01T00:00:00Z"}).status_code==422
    assert client.post("/posts",json={"title":"bad","content":"bad","expires_at":"2030-01-01T00:00:00"}).status_code==422


def test_admin_reset_force_change_and_audit(client,app,admin):
    result=client.post("/users/register",json={"username":"member","nickname":"Member","email":"member@example.com","password":PASSWORD})
    uid=result.json()["id"]
    with TestClient(app) as member_client:
        member_client.post("/users/login",json={"username":"member","password":PASSWORD})
        old_token=member_client.cookies.get("board_session")
        assert client.put(f"/users/admin/reset-password/{uid}",json={"password":"temporary-pass-123"}).status_code==200
        assert member_client.get("/users/me",headers={"Authorization":"Bearer "+old_token}).status_code==401
        assert member_client.post("/users/login",json={"username":"member","password":"temporary-pass-123"}).json()["must_change_password"] is True
        assert member_client.post("/posts",json={"title":"blocked","content":"blocked"}).status_code==403
        assert member_client.put("/users/update-password",json={"current_password":"wrong","password":"new-safe-pass-456"}).status_code==400
        changed=member_client.put("/users/update-password",json={"current_password":"temporary-pass-123","password":"new-safe-pass-456"})
        assert changed.status_code==200
        assert changed.json()["must_change_password"] is False
        assert member_client.post("/posts",json={"title":"allowed","content":"allowed"}).status_code==201
    assert client.get("/api/admin/stats").json()["users"]==2
    assert len(client.get("/api/admin/stats").json()["activity"])==7
    assert client.get("/api/admin/users?q=Member").json()["total"]==1
    assert client.get("/api/admin/system").json()["status"]=="ok"
    logs=client.get("/api/admin/audit-logs").json()["items"]
    assert any(log["action"]=="reset_password" for log in logs)
    assert "temporary-pass" not in str(logs)


def test_admin_moderation_and_cascade(client,app,admin):
    uid=client.post("/users/register",json={"username":"member","nickname":"Member","email":"member@example.com","password":PASSWORD}).json()["id"]
    with TestClient(app) as other:
        other.post("/users/login",json={"username":"member","password":PASSWORD})
        post=other.post("/posts",json={"title":"Member post","content":"test"}).json()
        reply=other.post(f"/posts/{post['id']}/replies",json={"content":"test"}).json()
    assert client.delete(f"/api/admin/replies/{reply['id']}").status_code==204
    assert client.put(f"/posts/{post['id']}",json={"title":"Moderated","content":"updated"}).status_code==200
    assert client.get("/api/admin/posts?status=all").json()["total"]==1
    assert client.delete(f"/users/{uid}").status_code==204
    assert client.get(f"/posts/{post['id']}").status_code==404
    assert client.delete(f"/users/{admin['id']}").status_code==400
    assert {l["action"] for l in client.get("/api/admin/audit-logs").json()["items"]} >= {"delete_reply","update_post","delete_user"}


def test_csrf_and_cookie_flags(client,member):
    assert client.post("/posts",json={"title":"x","content":"x"},headers={"Origin":"https://evil.example"}).status_code==403
    assert client.post("/users/login",json={"username":"alice","password":PASSWORD},headers={"Sec-Fetch-Site":"cross-site"}).status_code==403
    result=client.post("/users/login",json={"username":"alice","password":PASSWORD})
    cookie=result.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=lax" in cookie
    assert "no-store" in result.headers["cache-control"]


def test_rate_limiting(client):
    for i in range(10):assert client.post("/users/login",json={"username":"nobody","password":"incorrect"}).status_code==401
    assert client.post("/users/login",json={"username":"nobody","password":"incorrect"}).status_code==429


def test_docs_health_and_anonymous_access(client):
    assert client.get("/docs").status_code==200
    paths=client.get("/openapi.json").json()["paths"]
    for path in ["/users/register","/users/login","/users/update-password","/posts","/posts/{post_id}/replies","/api/admin/stats"]:assert path in paths
    assert client.get("/health").json()["status"]=="ok"
    assert client.get("/api/health").status_code==200
    assert client.post("/posts",json={"title":"test","content":"test"}).status_code==401
    assert client.get("/api/admin/users").status_code==401
