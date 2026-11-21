from datetime import timedelta
from app.core.set_pins import set_pins
from app.models.entities import Post, PostPin, utcnow


def test_pins_precede_latest_and_popular_with_correct_pagination(client, member, app):
    ids = [client.post("/posts",json={"title":f"Pin example {i}","content":"test"}).json()["id"] for i in range(3)]
    for _ in range(2): client.post(f"/posts/{ids[2]}/replies",json={"content":"popular reply"})
    set_pins(app.state.settings,{ids[0]:2,ids[1]:1})
    for sort in ["latest","popular"]:
        result=client.get(f"/posts?sort={sort}&page_size=1").json()
        assert result["total"]==3
        assert result["items"][0]["id"]==ids[0]
        assert result["items"][0]["is_pinned"] is True
        assert client.get(f"/posts?sort={sort}&page=2&page_size=1").json()["items"][0]["id"]==ids[1]
        assert client.get(f"/posts?sort={sort}&page=3&page_size=1").json()["items"][0]["id"]==ids[2]
    assert client.get(f"/posts/{ids[2]}").json()["is_pinned"] is False
    assert client.get("/posts?q=example%202").json()["total"]==1


def test_pin_respects_expiration_and_deletion(client, member, app):
    post_id=client.post("/posts",json={"title":"Pinned","content":"test"}).json()["id"]
    set_pins(app.state.settings,{post_id:1})
    with app.state.session_factory() as db:
        db.get(Post,post_id).expires_at=utcnow()-timedelta(seconds=1);db.commit()
    assert client.get("/posts").json()["total"]==0
    assert client.get("/posts/mine").json()["items"][0]["is_pinned"] is True
    assert client.delete(f"/posts/{post_id}").status_code==204
    with app.state.session_factory() as db:
        assert db.get(PostPin,post_id) is None
