from datetime import timedelta
import bcrypt
import jwt
from app.models.entities import utcnow

DUMMY_HASH = bcrypt.hashpw(b"dummy-password-for-timing", bcrypt.gensalt()).decode()

def hash_password(password):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(password, hashed):
    try:
        return bcrypt.checkpw(password.encode(), hashed.encode())
    except (ValueError, TypeError):
        return False

def issue_token(user, settings):
    now = utcnow()
    return jwt.encode({"sub": str(user.id), "ver": user.token_version, "iat": now, "exp": now+timedelta(minutes=settings.token_minutes), "iss": "common-ground", "aud": "common-ground-web"}, settings.secret_key, algorithm="HS256")
