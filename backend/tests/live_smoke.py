"""Optional localhost-only smoke test against running Vite and FastAPI.
Creates random, disposable QA accounts and removes only those exact accounts.
Run from backend/: python tests/live_smoke.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import secrets
import subprocess
import uuid
import httpx
from sqlalchemy import select, delete
from app.core.config import Settings
from app.db.session import make_database
from app.models.entities import User, AuditLog

BASE="http://127.0.0.1:5173"
suffix=uuid.uuid4().hex[:10]
member_name="qa_member_"+suffix
admin_name="qa_admin_"+suffix
password=secrets.token_urlsafe(24)
temporary=secrets.token_urlsafe(24)
new_password=secrets.token_urlsafe(24)
member=httpx.Client();admin=httpx.Client()
member.headers["Origin"]=BASE;admin.headers["Origin"]=BASE
settings=Settings();engine,factory=make_database(settings.database_url)
checks=[]
def check(condition,label):
    if not condition:raise AssertionError(label)
    checks.append(label);print("PASS:",label)
def send(session,method,path,payload=None,status=200):
    response=session.request(method,BASE+"/api"+path,json=payload,timeout=15)
    if response.status_code!=status:raise AssertionError(f"{method} {path}: {response.status_code} {response.text}")
    return response
try:
    check(httpx.get(BASE,timeout=10).status_code==200,"Vite serves frontend HTML")
    check(httpx.get("http://127.0.0.1:8000/docs",timeout=10).status_code==200,"Swagger is available")
    check(send(member,"GET","/health").json()["version"]=="1.0.0","Vite proxy reaches new backend")
    u=send(member,"POST","/users/register",{"username":member_name,"nickname":"QA member","email":member_name+"@example.com","password":password},201).json()
    login=send(member,"POST","/users/login",{"username":member_name,"password":password})
    check("HttpOnly" in login.headers.get("Set-Cookie",""),"Login cookie survives Vite proxy")
    post=send(member,"POST","/posts",{"title":"QA temporary post "+suffix,"content":"Disposable integration check"},201).json()
    send(member,"POST",f"/posts/{post['id']}/replies",{"content":"QA reply"},201)
    check(send(member,"GET",f"/posts/{post['id']}").json()["reply_count"]==1,"Member registers, logs in, posts and replies")
    send(member,"GET","/admin/users",status=403)
    result=subprocess.run([sys.executable,"-X","utf8","-m","app.core.create_admin","--username",admin_name,"--email",admin_name+"@example.com","--nickname","QA admin","--password-stdin"],input=password+"\n"+password+"\n",capture_output=True,text=True,encoding="utf-8",timeout=20)
    check(result.returncode==0,"Local administrator CLI creates a protected administrator")
    send(admin,"POST","/users/login",{"username":admin_name,"password":password})
    check(send(admin,"GET","/admin/stats").json()["users"]>=2,"Admin dashboard reads live statistics")
    check(send(admin,"GET","/admin/users?q="+member_name).json()["total"]==1,"Admin user search reaches database")
    send(admin,"PUT",f"/posts/{post['id']}",{"title":"QA moderated "+suffix,"content":"Moderated"})
    check(send(admin,"GET","/admin/posts?q="+suffix).json()["total"]==1,"Admin can edit and search posts")
    send(admin,"PUT",f"/users/admin/reset-password/{u['id']}",{"password":temporary})
    send(member,"GET","/users/me",status=401)
    check(send(member,"POST","/users/login",{"username":member_name,"password":temporary}).json()["must_change_password"],"Reset invalidates old session and requires password change")
    send(member,"POST","/posts",{"title":"Blocked","content":"Blocked"},403)
    send(member,"PUT","/users/update-password",{"current_password":temporary,"password":new_password})
    check(not send(member,"GET","/users/me").json()["must_change_password"],"Forced password change restores member access")
    check(any(log["action"]=="reset_password" for log in send(admin,"GET","/admin/audit-logs").json()["items"]),"Admin actions are audited")
    send(member,"POST","/users/logout",status=204)
    send(member,"GET","/users/me",status=401)
    check(True,"Logout invalidates session through proxy")
finally:
    with factory() as db:
        qa_users=db.scalars(select(User).where(User.username.in_([member_name,admin_name]))).all()
        ids=[u.id for u in qa_users]
        if ids:db.execute(delete(AuditLog).where(AuditLog.actor_id.in_(ids)))
        for user in qa_users:db.delete(user)
        db.commit()
    engine.dispose()
    member.close();admin.close()
    print("Disposable QA accounts cleaned up")
print(f"Live smoke: {len(checks)} checks passed")
