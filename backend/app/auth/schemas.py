from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, model_validator


class UserRegister(BaseModel):
    email: EmailStr
    password: str
    organization_name: str

class ProfileUpdate(BaseModel):
    display_name: str = Field(..., min_length=1, max_length=255)

class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8, max_length=128)
    confirm_password: str = Field(..., min_length=8, max_length=128)

    @model_validator(mode="after")
    def passwords_match(self):
        if self.new_password != self.confirm_password:
            raise ValueError("New password and confirmation do not match.")
        if self.current_password == self.new_password:
            raise ValueError("New password must be different from the current password.")
        return self


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str


class UserResponse(BaseModel):
    id: int
    email: str
    organization_id: int
    role: str
    display_name: str | None = None
    created_at: datetime

    model_config = {
        "from_attributes": True
    }
