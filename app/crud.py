from sqlalchemy.orm import Session
from . import models, schemas, auth, minio_utils
from .auth import get_password_hash, verify_password
import jwt
from app.models import Notification
from fastapi import UploadFile

def create_user(db: Session, user: schemas.UserCreate):
    hashed_password = get_password_hash(user.password)
    db_user = models.User(
        email=user.email,
        password_hash=hashed_password,
        first_name=user.first_name,
        last_name=user.last_name,
        phone_number=user.phone_number
    )   
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def authenticate_user(db: Session, email: str, password: str):
    user = db.query(models.User).filter(models.User.email == email).first()
    if user and verify_password(password, user.password_hash):
        return user
    return False

def create_post(db: Session, post: schemas.PostCreate, user_id: int, file_url: str = None):
    db_post = models.Post(content=post.content, user_id=user_id, file_url=file_url)
    db.add(db_post)
    db.commit()
    db.refresh(db_post)
    return db_post

def get_posts(db: Session, user_id: int):
    return db.query(models.Post).order_by(models.Post.timestamp.desc()).all()


def create_notification(db: Session, notification: schemas.NotificationCreate, user_id: int):
    db_notification = models.Notification(post_id=notification.post_id, user_id = user_id, message=notification.message)
    db.add(db_notification)
    db.commit()
    db.refresh(db_notification)
    return db_notification

def get_notifications(db: Session, user_id: int):
    return db.query(models.Notification).filter(models.Notification.user_id != user_id).order_by(models.Notification.timestamp.desc()).all()


def get_user_from_token(db: Session, token: str):
    try:
        payload = jwt.decode(token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])
        email = payload.get("sub")
        if email is None:
            return None  # or raise an exception if preferred
    except jwt.PyJWTError:
        return None  # or raise an exception if preferred

    user = db.query(models.User).filter(models.User.email == email).first()
    return user

def mark_notifications_as_seen(db: Session, user_id: int):
    db.query(Notification).filter(Notification.user_id != user_id, Notification.seen == False).update({"seen": True})
    db.commit()
