import os
import subprocess
import sys
from sqlalchemy import select
from app.core.config import BASE_DIR
from app.db.session import make_database
from app.models.entities import User, AuditLog
from app.core.security import verify_password


def test_admin_cli_safe_stdin(tmp_path):
    url=f"sqlite:///{tmp_path / 'cli.db'}"
    env={**os.environ,"DATABASE_URL":url,"SECRET_KEY":"cli-test-only-"+"x"*48}
    password="cli-safe-password-123"
    command=[sys.executable,"-X","utf8","-m","app.core.create_admin","--username","cliadmin","--email","cliadmin@example.com","--password-stdin"]
    result=subprocess.run(command,input=password+"\n"+password+"\n",capture_output=True,text=True,encoding="utf-8",env=env,cwd=BASE_DIR,timeout=20)
    assert result.returncode==0,result.stderr
    assert password not in result.stdout+result.stderr
    engine,factory=make_database(url)
    with factory() as db:
        user=db.scalar(select(User))
        assert user.is_admin
        assert verify_password(password,user.hashed_password)
        assert db.scalar(select(AuditLog)).action=="create_admin_cli"
    repeated=subprocess.run(command,input=password+"\n"+password+"\n",capture_output=True,text=True,encoding="utf-8",env=env,cwd=BASE_DIR,timeout=20)
    assert repeated.returncode!=0
    assert "Username already exists" in repeated.stderr
    engine.dispose()


def test_admin_cli_rejects_mismatched_passwords(tmp_path):
    env={**os.environ,"DATABASE_URL":f"sqlite:///{tmp_path / 'cli.db'}","SECRET_KEY":"cli-test-only-"+"x"*48}
    result=subprocess.run([sys.executable,"-X","utf8","-m","app.core.create_admin","--username","cliadmin","--email","cliadmin@example.com","--password-stdin"],input="first-password-123\nother-password-123\n",capture_output=True,text=True,encoding="utf-8",env=env,cwd=BASE_DIR,timeout=20)
    assert result.returncode!=0
    assert "Passwords do not match" in result.stderr
