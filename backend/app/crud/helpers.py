from fastapi import HTTPException
from sqlalchemy import select, func, or_
from app.models.entities import Post, Reply, User, AuditLog, PostLike, PostLikeBaseline, PostPin, utcnow, aware

def audit(db, actor, action, target):
    db.add(AuditLog(actor_id=actor.id, actor_name=actor.username, action=action, target=str(target)))

def require_item(db, model, identifier):
    item = db.get(model, identifier)
    if item is None:
        raise HTTPException(404, "找不到資料")
    return item

def owner_or_admin(user, owner_id):
    if not user.is_admin and user.id != owner_id:
        raise HTTPException(403, "沒有操作此資料的權限")

def reply_out(reply):
    return {"id": reply.id, "post_id": reply.post_id, "author_id": reply.author_id, "author_name": reply.author_name, "content": reply.content, "created_at": aware(reply.created_at)}

def like_summary(db, post_id, viewer_id=None):
    real_count = db.scalar(select(func.count()).select_from(PostLike).where(PostLike.post_id == post_id))
    baseline = db.get(PostLikeBaseline, post_id)
    demo_count = baseline.count if baseline else 0
    liked = viewer_id is not None and db.get(PostLike, (post_id, viewer_id)) is not None
    return {"like_count": real_count + demo_count, "real_like_count": real_count,
            "demo_like_count": demo_count, "liked_by_me": liked}


def post_out(db, post, detail=False, viewer_id=None):
    data = {key: getattr(post, key) for key in ["id", "author_id", "author_name", "title", "content", "remarks"]}
    data.update(created_at=aware(post.created_at), expires_at=aware(post.expires_at), is_expired=aware(post.expires_at)<=utcnow(), reply_count=db.scalar(select(func.count(Reply.id)).where(Reply.post_id==post.id)))
    data["is_pinned"] = db.get(PostPin, post.id) is not None
    data.update(like_summary(db, post.id, viewer_id))
    if detail:
        data["replies"] = [reply_out(r) for r in db.scalars(select(Reply).where(Reply.post_id==post.id).order_by(Reply.id))]
    return data

def post_page(db, q, page, page_size, status="active", author_id=None, sort="latest", viewer_id=None):
    query = select(Post).outerjoin(PostPin, PostPin.post_id == Post.id)
    if status == "active": query = query.where(Post.expires_at > utcnow())
    elif status == "expired": query = query.where(Post.expires_at <= utcnow())
    if author_id is not None: query = query.where(Post.author_id == author_id)
    if q: query = query.where(or_(Post.title.contains(q, autoescape=True), Post.content.contains(q, autoescape=True), Post.author_name.contains(q, autoescape=True)))
    total = db.scalar(select(func.count()).select_from(query.subquery()))
    query = query.order_by(func.coalesce(PostPin.priority, 0).desc())
    if sort == "popular": query = query.order_by(select(func.count(Reply.id)).where(Reply.post_id==Post.id).correlate(Post).scalar_subquery().desc(), Post.id.desc())
    else: query = query.order_by(Post.id.desc())
    items = db.scalars(query.offset((page-1)*page_size).limit(page_size)).all()
    return {"items": [post_out(db, p, viewer_id=viewer_id) for p in items], "total": total, "page": page, "page_size": page_size}
