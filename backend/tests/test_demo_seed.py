from sqlalchemy import select, func
import pytest
from app.core.seed_demo import seed_demo
from app.core.security import verify_password
from app.models.entities import User, Post, utcnow, aware


def test_seed_creates_six_accounts_and_18_active_posts_without_touching_existing(app, client, member):
    result=seed_demo(app.state.settings)
    assert [item["posts"] for item in result]==[2,3,4,2,3,4]
    assert len({item["password"] for item in result})==6
    with app.state.session_factory() as db:
        assert db.scalar(select(func.count(User.id)))==7
        assert db.scalar(select(func.count(Post.id)))==18
        assert db.get(User,member["id"]).username=="alice"
        for item in result:
            user=db.scalar(select(User).where(User.username==item["username"]))
            assert not user.is_admin
            assert verify_password(item["password"],user.hashed_password)
            posts=db.scalars(select(Post).where(Post.author_id==user.id)).all()
            assert len(posts)==item["posts"]
            assert all(aware(post.expires_at)>utcnow() for post in posts)
            assert all("測試資料" in post.remarks and "threads.com/" in post.remarks for post in posts)
    listing=client.get("/posts?page_size=100").json()
    assert listing["total"]==18
    assert len({post["author_id"] for post in listing["items"][:6]})>1


def test_seed_refuses_duplicates_without_changing_existing_accounts(app, client):
    result=seed_demo(app.state.settings)
    with pytest.raises(ValueError):seed_demo(app.state.settings)
    with app.state.session_factory() as db:
        assert db.scalar(select(func.count(User.id)))==6
        assert db.scalar(select(func.count(Post.id)))==18
        user=db.scalar(select(User).where(User.username==result[0]["username"]))
        assert verify_password(result[0]["password"],user.hashed_password)
