from typing import Literal
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import delete
from sqlalchemy.dialects.sqlite import insert
from app.api.dependencies import get_db, active_user, optional_user
from app.models.entities import Post, Reply, PostLike, utcnow, aware
from app.schemas.contracts import PostInput, ReplyInput
from app.crud.helpers import post_page, post_out, reply_out, require_item, owner_or_admin, audit, like_summary

router=APIRouter(prefix="/posts", tags=["posts"])

@router.get("")
def list_posts(q: str=Query("", max_length=200), page: int=Query(1,ge=1), page_size: int=Query(9,ge=1,le=100), sort: Literal["latest","popular"]="latest", viewer=Depends(optional_user), db=Depends(get_db)):
    return post_page(db,q,page,page_size,sort=sort,viewer_id=viewer.id if viewer else None)

@router.get("/mine")
def my_posts(q: str=Query("",max_length=200), page: int=Query(1,ge=1), page_size: int=Query(9,ge=1,le=100), sort: Literal["latest","popular"]="latest", user=Depends(active_user), db=Depends(get_db)):
    return post_page(db,q,page,page_size,"all",user.id,sort,viewer_id=user.id)

@router.post("",status_code=201)
def create_post(data: PostInput,user=Depends(active_user),db=Depends(get_db)):
    values=data.model_dump(exclude={"expires_at"})
    post=Post(**values,author_id=user.id,author_name=user.nickname,expires_at=data.expires_at or utcnow()+timedelta(days=7))
    db.add(post)
    if user.is_admin: audit(db,user,"create_post",data.title)
    db.commit()
    return post_out(db,post,True,viewer_id=user.id)

@router.get("/{post_id}")
def get_post(post_id:int,viewer=Depends(optional_user),db=Depends(get_db)):
    return post_out(db,require_item(db,Post,post_id),True,viewer_id=viewer.id if viewer else None)

@router.put("/{post_id}")
def update_post(post_id:int,data:PostInput,user=Depends(active_user),db=Depends(get_db)):
    post=require_item(db,Post,post_id);owner_or_admin(user,post.author_id)
    for key,value in data.model_dump(exclude_unset=True).items():
        if key!="expires_at" or value is not None: setattr(post,key,value)
    if user.is_admin: audit(db,user,"update_post",f"post:{post.id}")
    db.commit();return post_out(db,post,True,viewer_id=user.id)

@router.delete("/{post_id}",status_code=204)
def delete_post(post_id:int,user=Depends(active_user),db=Depends(get_db)):
    post=require_item(db,Post,post_id);owner_or_admin(user,post.author_id)
    if user.is_admin: audit(db,user,"delete_post",f"post:{post.id}:{post.title}")
    db.delete(post);db.commit()

@router.post("/{post_id}/replies",status_code=201)
def create_reply(post_id:int,data:ReplyInput,user=Depends(active_user),db=Depends(get_db)):
    post=require_item(db,Post,post_id)
    if aware(post.expires_at)<=utcnow():raise HTTPException(409,"文章已過期，無法新增回覆")
    reply=Reply(post_id=post.id,author_id=user.id,author_name=user.nickname,content=data.content)
    db.add(reply);db.commit();return reply_out(reply)


@router.post("/{post_id}/likes")
def like_post(post_id: int, user=Depends(active_user), db=Depends(get_db)):
    post = require_item(db, Post, post_id)
    if aware(post.expires_at) <= utcnow():
        raise HTTPException(409, "文章已過期，無法新增愛心")
    db.execute(insert(PostLike).values(post_id=post_id, user_id=user.id).on_conflict_do_nothing(index_elements=["post_id", "user_id"]))
    db.commit()
    return {"post_id": post_id, **like_summary(db, post_id, user.id)}


@router.delete("/{post_id}/likes")
def unlike_post(post_id: int, user=Depends(active_user), db=Depends(get_db)):
    require_item(db, Post, post_id)
    db.execute(delete(PostLike).where(PostLike.post_id == post_id, PostLike.user_id == user.id))
    db.commit()
    return {"post_id": post_id, **like_summary(db, post_id, user.id)}
