import platform
from datetime import timedelta
from typing import Literal
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, or_
from app.api.dependencies import get_db, admin_user
from app.models.entities import User,Post,Reply,AuditLog,utcnow,aware
from app.schemas.contracts import UserOut
from app.crud.helpers import post_page, require_item, audit

router=APIRouter(prefix="/admin",tags=["admin"],dependencies=[Depends(admin_user)])

@router.get("/stats")
def stats(db=Depends(get_db)):
    count=lambda model: db.scalar(select(func.count()).select_from(model))
    now=utcnow()
    activity=[]
    for offset in range(6,-1,-1):
        start=(now-timedelta(days=offset)).replace(hour=0,minute=0,second=0,microsecond=0)
        end=start+timedelta(days=1)
        activity.append({"date":start.date().isoformat(),"posts":db.scalar(select(func.count(Post.id)).where(Post.created_at>=start,Post.created_at<end)),"replies":db.scalar(select(func.count(Reply.id)).where(Reply.created_at>=start,Reply.created_at<end))})
    return {"users":count(User),"posts":count(Post),"replies":count(Reply),"active_posts":db.scalar(select(func.count(Post.id)).where(Post.expires_at>now)),"recent_users":[UserOut.model_validate(u) for u in db.scalars(select(User).order_by(User.id.desc()).limit(5))],"recent_posts":[{"id":p.id,"title":p.title,"author_name":p.author_name,"created_at":aware(p.created_at)} for p in db.scalars(select(Post).order_by(Post.id.desc()).limit(5))],"activity":activity}

@router.get("/users")
def users(q:str=Query("",max_length=200),page:int=Query(1,ge=1),page_size:int=Query(10,ge=1,le=100),db=Depends(get_db)):
    query=select(User)
    if q:query=query.where(or_(User.username.contains(q,autoescape=True),User.nickname.contains(q,autoescape=True),User.email.contains(q,autoescape=True)))
    total=db.scalar(select(func.count()).select_from(query.subquery()))
    return {"items":[UserOut.model_validate(u) for u in db.scalars(query.order_by(User.id.desc()).offset((page-1)*page_size).limit(page_size))],"total":total,"page":page,"page_size":page_size}

@router.get("/posts")
def posts(q:str=Query("",max_length=200),status:Literal["all","active","expired"]="all",page:int=Query(1,ge=1),page_size:int=Query(10,ge=1,le=100),db=Depends(get_db)):
    return post_page(db,q,page,page_size,status)

@router.delete("/replies/{reply_id}",status_code=204)
def delete_reply(reply_id:int,user=Depends(admin_user),db=Depends(get_db)):
    reply=require_item(db,Reply,reply_id);audit(db,user,"delete_reply",f"reply:{reply.id}:post:{reply.post_id}")
    db.delete(reply);db.commit()

@router.get("/audit-logs")
def logs(page:int=Query(1,ge=1),page_size:int=Query(20,ge=1,le=100),db=Depends(get_db)):
    return {"items":[{"id":l.id,"actor_name":l.actor_name,"action":l.action,"target":l.target,"created_at":aware(l.created_at)} for l in db.scalars(select(AuditLog).order_by(AuditLog.id.desc()).offset((page-1)*page_size).limit(page_size))],"total":db.scalar(select(func.count(AuditLog.id))),"page":page,"page_size":page_size}

@router.get("/system")
def system(db=Depends(get_db)):
    db.execute(select(1))
    return {"status":"ok","python":platform.python_version(),"database":"SQLite / SQLAlchemy 2","timezone":"UTC","authentication":"HttpOnly JWT / revocable sessions","version":"1.0.0"}
