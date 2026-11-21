from fastapi import Request, Depends, HTTPException
import jwt
from app.models.entities import User

def get_db(request: Request):
    with request.app.state.session_factory() as db:
        yield db

def current_user(request: Request, db=Depends(get_db)):
    token = request.cookies.get("board_session")
    header = request.headers.get("authorization", "")
    if header.startswith("Bearer "):
        token = header[7:]
    if not token:
        raise HTTPException(401, "請先登入")
    try:
        data = jwt.decode(token, request.app.state.settings.secret_key, algorithms=["HS256"], audience="common-ground-web", issuer="common-ground", options={"require": ["sub", "ver", "iat", "exp"]})
        user = db.get(User, int(data["sub"]))
        if user is None or user.token_version != data["ver"]:
            raise ValueError()
    except (jwt.PyJWTError, ValueError, KeyError, TypeError):
        raise HTTPException(401, "登入已失效，請重新登入")
    return user

def active_user(user=Depends(current_user)):
    if user.must_change_password:
        raise HTTPException(403, "請先修改管理員重設的密碼")
    return user

def admin_user(user=Depends(active_user)):
    if not user.is_admin:
        raise HTTPException(403, "此操作需要管理員權限")
    return user


def optional_user(request: Request, db=Depends(get_db)):
    """Public reads remain available; a valid session personalizes like state."""
    try:
        return current_user(request, db)
    except HTTPException as error:
        if error.status_code == 401:
            return None
        raise
