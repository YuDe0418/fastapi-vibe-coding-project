from collections import defaultdict, deque
from threading import Lock
from time import monotonic
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from app.api.dependencies import get_db, current_user, active_user, admin_user
from app.schemas.contracts import Register, Login, UserUpdate, UserOut, PasswordInput, PasswordChange
from app.models.entities import User
from app.core.security import hash_password, verify_password, issue_token, DUMMY_HASH
from app.crud.helpers import owner_or_admin, require_item, audit

router = APIRouter(prefix="/users", tags=["users"])

def session_cookie(response, user, settings):
    response.set_cookie("board_session", issue_token(user, settings), httponly=True, secure=settings.cookie_secure, samesite="lax", max_age=settings.token_minutes*60, path="/")

def commit_user(db):
    try: db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "帳號或電子郵件已被使用")

@router.post("/register", response_model=UserOut, status_code=201)
def register(data: Register, db=Depends(get_db)):
    user = User(username=data.username.lower(), nickname=data.nickname, email=str(data.email).lower(), hashed_password=hash_password(data.password))
    db.add(user); commit_user(db)
    return user

@router.post("/login", response_model=UserOut)
def login(data: Login, request: Request, response: Response, db=Depends(get_db)):
    host = request.client.host if request.client else "unknown"
    now = monotonic()
    with request.app.state.login_lock:
        attempts = request.app.state.login_attempts
        # Limit both source IP and account to prevent simple username/IP rotation.
        for key in list(attempts):
            while attempts[key] and attempts[key][0] < now-900: attempts[key].popleft()
            if not attempts[key]: del attempts[key]
        keys = ["ip:"+host, "user:"+data.username.lower()]
        if any(len(attempts.get(key, [])) >= 10 for key in keys):
            raise HTTPException(429, "登入嘗試過多，請於 15 分鐘後再試", headers={"Retry-After": "900"})
        for key in keys: attempts.setdefault(key, deque()).append(now)
    user = db.scalar(select(User).where(User.username==data.username.lower()))
    valid = verify_password(data.password, user.hashed_password if user else DUMMY_HASH)
    if not user or not valid: raise HTTPException(401, "帳號或密碼錯誤")
    session_cookie(response, user, request.app.state.settings)
    return user

@router.get("/me", response_model=UserOut)
def me(user=Depends(current_user)):
    return user

@router.post("/logout", status_code=204)
def logout(response: Response, user=Depends(current_user), db=Depends(get_db)):
    user.token_version += 1; db.commit()
    response.delete_cookie("board_session", path="/")

@router.put("/update-password", response_model=UserOut)
def update_password(data: PasswordChange, request: Request, response: Response, user=Depends(current_user), db=Depends(get_db)):
    if not verify_password(data.current_password, user.hashed_password): raise HTTPException(400, "目前密碼不正確")
    if verify_password(data.password, user.hashed_password): raise HTTPException(400, "新密碼不可與目前密碼相同")
    user.hashed_password=hash_password(data.password); user.must_change_password=False; user.token_version+=1
    if user.is_admin: audit(db, user, "change_password", f"user:{user.id}")
    db.commit(); session_cookie(response, user, request.app.state.settings)
    return user

@router.put("/admin/reset-password/{user_id}", response_model=UserOut)
def reset_password(user_id: int, data: PasswordInput, admin=Depends(admin_user), db=Depends(get_db)):
    user = require_item(db, User, user_id)
    user.hashed_password=hash_password(data.password); user.must_change_password=True; user.token_version+=1
    audit(db, admin, "reset_password", f"user:{user.id}"); db.commit()
    return user

@router.put("/{user_id}", response_model=UserOut)
def update_user(user_id: int, data: UserUpdate, user=Depends(active_user), db=Depends(get_db)):
    owner_or_admin(user, user_id)
    target=require_item(db, User, user_id)
    for key, value in data.model_dump().items(): setattr(target, key, str(value).lower() if key=="email" else value)
    if user.is_admin: audit(db, user, "update_user", f"user:{target.id}")
    commit_user(db)
    return target

@router.delete("/{user_id}", status_code=204)
def delete_user(user_id: int, user=Depends(active_user), db=Depends(get_db)):
    owner_or_admin(user, user_id)
    target=require_item(db, User, user_id)
    if target.is_admin: raise HTTPException(400, "請保留管理員帳號，禁止從網站刪除管理員")
    if user.is_admin: audit(db, user, "delete_user", f"user:{target.id}:{target.username}")
    db.delete(target); db.commit()
