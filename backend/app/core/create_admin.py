import argparse
import sys
from getpass import getpass
from sqlalchemy import select
from app.core.config import Settings
from app.core.security import hash_password
from app.db.session import Base, make_database
from app.models.entities import User, AuditLog
from app.schemas.contracts import Register

def main():
    parser=argparse.ArgumentParser(description="Create administrator locally; never exposes a public promotion endpoint")
    parser.add_argument("--username",required=True);parser.add_argument("--email",required=True);parser.add_argument("--nickname",default="管理員")
    parser.add_argument("--password-stdin",action="store_true",help="Read password and confirmation as two lines from stdin, for local automation")
    args=parser.parse_args()
    if args.password_stdin:
        password=sys.stdin.readline().rstrip("\r\n")
        confirmation=sys.stdin.readline().rstrip("\r\n")
    else:
        password=getpass("Admin password (10+ characters): ")
        confirmation=getpass("Confirm password: ")
    if password!=confirmation:raise SystemExit("Passwords do not match")
    data=Register(username=args.username,email=args.email,nickname=args.nickname,password=password)
    settings=Settings();settings.validate_secret()
    engine,factory=make_database(settings.database_url);Base.metadata.create_all(engine)
    with factory() as db:
        if db.scalar(select(User).where(User.username==data.username.lower())):raise SystemExit("Username already exists; existing users will not be promoted")
        user=User(username=data.username.lower(),nickname=data.nickname,email=str(data.email).lower(),hashed_password=hash_password(data.password),is_admin=True)
        db.add(user);db.flush();db.add(AuditLog(actor_id=user.id,actor_name=user.username,action="create_admin_cli",target=f"user:{user.id}"));db.commit()
        print("Administrator created")
    engine.dispose()

if __name__=="__main__":main()
