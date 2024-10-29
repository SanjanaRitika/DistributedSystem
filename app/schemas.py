from pydantic import BaseModel
from datetime import datetime

# User schemas
class UserCreate(BaseModel):
    email: str
    password: str
    first_name: str
    last_name: str
    phone_number: str

class UserResponse(BaseModel):
    id: int
    email: str
    first_name: str
    last_name: str
    phone_number: str
    created_at: datetime
    password :str

    class Config:
        from_attributes = True

class UserLogin(BaseModel):
    email: str
    password: str

# Post schemas
class PostCreate(BaseModel):
    content: str

class PostResponse(BaseModel):
    id: int
    content: str
    timestamp: datetime

# Notification schemas
class NotificationCreate(BaseModel):
    user_id: int
    post_id: int
    message: str

class NotificationResponse(BaseModel):
    id: int
    post_id: int
    message: str
    timestamp: datetime
