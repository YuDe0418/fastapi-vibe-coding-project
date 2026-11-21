from datetime import timedelta
import sqlite3
from sqlalchemy import select, func
from app.core.set_demo_likes import set_counts
from app.core.config import Settings
from app.db.session import make_database, Base
from app.models.entities import Post, PostLike, PostLikeBaseline, utcnow


def make_post(client):
    result = client.post("/posts", json={"title": "Like me", "content": "Hello"})
    assert result.status_code == 201
    return result.json()["id"]


def test_like_unlike_idempotency_and_persistence(client, member, app):
    post_id = make_post(client)
    path = f"/posts/{post_id}/likes"
    assert client.get(f"/posts/{post_id}").json()["like_count"] == 0
    for _ in range(2):
        result = client.post(path)
        assert result.status_code == 200
        assert result.json()["like_count"] == 1
        assert result.json()["liked_by_me"] is True
    assert client.get("/posts").json()["items"][0]["liked_by_me"] is True
    assert client.get("/posts/mine").json()["items"][0]["liked_by_me"] is True
    assert client.get(f"/posts/{post_id}").json()["real_like_count"] == 1
    with app.state.session_factory() as db:
        assert db.scalar(select(func.count()).select_from(PostLike)) == 1
    for _ in range(2):
        result = client.delete(path)
        assert result.status_code == 200
        assert result.json()["like_count"] == 0
        assert result.json()["liked_by_me"] is False


def test_user_specific_likes_and_anonymous_access(client, member):
    post_id = make_post(client)
    client.post(f"/api/posts/{post_id}/likes")
    client.post("/users/logout")
    public = client.get(f"/posts/{post_id}")
    assert public.json()["like_count"] == 1
    assert public.json()["liked_by_me"] is False
    assert public.headers["cache-control"] == "no-store"
    assert client.post(f"/posts/{post_id}/likes").status_code == 401
    assert client.delete(f"/posts/{post_id}/likes").status_code == 401
    client.post("/users/register", json={"username": "second", "nickname": "Second", "email": "second@example.com", "password": "second-password-123"})
    client.post("/users/login", json={"username": "second", "password": "second-password-123"})
    assert client.get(f"/posts/{post_id}").json()["liked_by_me"] is False
    assert client.post(f"/posts/{post_id}/likes").json()["like_count"] == 2
    assert client.delete(f"/posts/{post_id}/likes").json()["like_count"] == 1


def test_demo_baseline_is_separate_and_never_decremented(client, member, app):
    post_id = make_post(client)
    set_counts(app.state.settings, {post_id: 24300})
    result = client.get(f"/posts/{post_id}").json()
    assert result["like_count"] == 24300
    assert result["demo_like_count"] == 24300
    assert result["real_like_count"] == 0
    assert client.post(f"/posts/{post_id}/likes").json()["like_count"] == 24301
    assert client.delete(f"/posts/{post_id}/likes").json()["like_count"] == 24300
    with app.state.session_factory() as db:
        assert db.scalar(select(func.count()).select_from(PostLike)) == 0
    set_counts(app.state.settings, {post_id: 45800})
    assert client.get(f"/posts/{post_id}").json()["like_count"] == 45800


def test_expiration_missing_posts_and_delete_cascade(client, member, app):
    post_id = make_post(client)
    assert client.post("/posts/999999/likes").status_code == 404
    assert client.delete("/posts/999999/likes").status_code == 404
    client.post(f"/posts/{post_id}/likes")
    set_counts(app.state.settings, {post_id: 10})
    with app.state.session_factory() as db:
        db.get(Post, post_id).expires_at = utcnow() - timedelta(seconds=1)
        db.commit()
    assert client.post(f"/posts/{post_id}/likes").status_code == 409
    assert client.delete(f"/posts/{post_id}/likes").json()["like_count"] == 10
    assert client.delete(f"/posts/{post_id}").status_code == 204
    with app.state.session_factory() as db:
        assert db.scalar(select(func.count()).select_from(PostLike)) == 0
        assert db.scalar(select(func.count()).select_from(PostLikeBaseline)) == 0


def test_additive_schema_preserves_old_post_table(tmp_path):
    path = tmp_path / "old.db"
    # A populated pre-likes table must not be ALTERed or replaced.
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE posts (id INTEGER PRIMARY KEY, author_id INTEGER NOT NULL, author_name TEXT NOT NULL, title TEXT NOT NULL, content TEXT NOT NULL, remarks TEXT NOT NULL, created_at DATETIME NOT NULL, expires_at DATETIME NOT NULL)")
        connection.execute("INSERT INTO posts VALUES (1,1,'A','Original','Kept','', '2026-11-17','2026-11-24')")
    engine, factory = make_database(f"sqlite:///{path}")
    Base.metadata.create_all(engine)
    with sqlite3.connect(path) as connection:
        assert connection.execute("SELECT title FROM posts WHERE id=1").fetchone()[0] == "Original"
        assert connection.execute("SELECT count(*) FROM post_likes").fetchone()[0] == 0
        assert connection.execute("SELECT count(*) FROM post_like_baselines").fetchone()[0] == 0
    engine.dispose()
