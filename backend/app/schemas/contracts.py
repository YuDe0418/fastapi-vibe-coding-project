from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
from app.models.entities import aware

class Input(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

class PasswordInput(Input):
    password: str = Field(min_length=10, max_length=72)
    @field_validator("password")
    @classmethod
    def password_bytes(cls, value):
        if len(value.encode()) > 72:
            raise ValueError("密碼 UTF-8 編碼不得超過 72 bytes")
        return value

class Register(PasswordInput):
    username: str = Field(min_length=3, max_length=32, pattern=r"^[a-zA-Z0-9_]+$")
    nickname: str = Field(min_length=1, max_length=50)
    email: EmailStr

class Login(Input):
    username: str = Field(min_length=1, max_length=32)
    password: str = Field(min_length=1, max_length=200)

class UserUpdate(Input):
    nickname: str = Field(min_length=1, max_length=50)
    email: EmailStr
    phone: str = Field(default="", max_length=30)
    address: str = Field(default="", max_length=300)

class PasswordChange(PasswordInput):
    current_password: str = Field(min_length=1, max_length=200)

class PostInput(Input):
    title: str = Field(min_length=1, max_length=160)
    content: str = Field(min_length=1, max_length=20000)
    remarks: str = Field(default="", max_length=500)
    expires_at: datetime | None = None
    @field_validator("expires_at")
    @classmethod
    def valid_expiry(cls, value):
        if value is not None:
            if value.tzinfo is None:
                raise ValueError("expires_at 必須包含時區")
            from app.models.entities import utcnow
            if value <= utcnow():
                raise ValueError("有效期限必須晚於現在")
        return value

class ReplyInput(Input):
    content: str = Field(min_length=1, max_length=4000)

class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    username: str
    nickname: str
    email: str
    phone: str
    address: str
    is_admin: bool
    must_change_password: bool
    created_at: datetime
    @field_validator("created_at")
    @classmethod
    def utc(cls, value):
        return aware(value)
