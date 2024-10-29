from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from . import crud, models, schemas, auth
from .database import engine, get_db
from fastapi.security import OAuth2PasswordBearer
from typing import List
from .schemas import UserResponse

app = FastAPI()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="signin")

# Custom exception handler for HTTPException
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )

# Custom exception handler for general exceptions
@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal server error occurred."}
    )

models.Base.metadata.create_all(bind=engine)

@app.post("/signup", response_model=schemas.UserResponse)
async def signup(user: schemas.UserCreate, db: Session = Depends(get_db)):
    try:
        new_user = crud.create_user(db, user)
        return UserResponse(
            id=new_user.id,
            email=new_user.email,
            first_name=new_user.first_name,
            last_name=new_user.last_name,
            phone_number=new_user.phone_number,
            created_at=new_user.created_at,
            password='***'  # It’s best to avoid sending sensitive data
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/signin")
async def signin(user: schemas.UserLogin, db: Session = Depends(get_db)):
    try:
        authenticated_user = crud.authenticate_user(db, user.email, user.password)
        if not authenticated_user:
            raise HTTPException(status_code=400, detail="Invalid credentials")
        access_token = auth.create_access_token(data={"sub": authenticated_user.email})
        return {"access_token": access_token, "token_type": "bearer"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# New Dependency for Current User
async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    current_user = crud.get_user_from_token(db, token)
    if current_user is None:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    return current_user

@app.get("/post", response_model=List[schemas.PostResponse])
async def get_posts(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    return crud.get_posts(db, user_id=current_user.id)

@app.post("/post", response_model=schemas.PostResponse)
async def create_post(post: schemas.PostCreate, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    return crud.create_post(db, post, user_id=current_user.id)

@app.get("/notification", response_model=List[schemas.NotificationResponse])
async def get_notifications(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    return crud.get_notifications(db)

@app.post("/notification", response_model=schemas.NotificationResponse)
async def create_notification(notification: schemas.NotificationCreate, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    return crud.create_notification(db, notification)
