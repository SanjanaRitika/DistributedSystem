from fastapi import FastAPI, Depends, HTTPException, Request, Form, UploadFile, File
from fastapi.responses import JSONResponse, RedirectResponse, HTMLResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
from fastapi.security import OAuth2PasswordBearer
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from typing import List
from . import crud, models, schemas, auth
from .minio_utils import upload_file_to_minio  # Import your MinIO utility
from .database import engine, get_db
from .schemas import UserResponse
from fastapi import Cookie
from .models import User
from .crud import mark_notifications_as_seen


app = FastAPI()

# Setting up Jinja2 templates
templates = Jinja2Templates(directory="app/templates")

# Mount static files (CSS, JS, etc.)
app.mount("/static", StaticFiles(directory="app/static"), name="static")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="signin")

# Exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    return JSONResponse(status_code=500, content={"detail": "An internal server error occurred."})

# Create DB tables
models.Base.metadata.create_all(bind=engine)

# Front-end routes

@app.get("/signup")
def signup_form(request: Request):
    return templates.TemplateResponse("signup.html", {"request": request})

@app.post("/signup")
async def signup(
    request: Request,
    first_name: str = Form(...),
    last_name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    phone_number: str = Form(...),
    db: Session = Depends(get_db)
):
    try:
        user = schemas.UserCreate(
            first_name=first_name,
            last_name=last_name,
            email=email,
            password=password,
            phone_number=phone_number
        )
        new_user = crud.create_user(db, user)
        return RedirectResponse("/signin", status_code=303)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/signin")
def signin_form(request: Request):
    return templates.TemplateResponse("signin.html", {"request": request})

@app.post("/signin")
async def signin(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    try:
        authenticated_user = crud.authenticate_user(db, email, password)
        if not authenticated_user:
            raise HTTPException(status_code=400, detail="Invalid credentials")

        access_token = auth.create_access_token(data={"sub": authenticated_user.email})
        response = RedirectResponse("/", status_code=303)
        response.set_cookie(key="access_token", value=f"Bearer {access_token}")
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Dependency to get current user
async def get_current_user(access_token: str = Cookie(None), db: Session = Depends(get_db)):
    if access_token is None:
        raise HTTPException(status_code=401, detail="Not authenticated")

    # Remove "Bearer " prefix
    token = access_token.split(" ")[1] if access_token.startswith("Bearer ") else access_token

    # Log token for debugging
    print(f"Access token: {token}")

    current_user = crud.get_user_from_token(db, token)
    
    if current_user is None:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")

    return current_user

@app.get("/", response_class=HTMLResponse)
async def home(request: Request, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    posts = crud.get_posts(db, current_user.id)
    notifications = crud.get_notifications(db, current_user.id)
    
    return templates.TemplateResponse(
        "home.html",  # Assuming index.html is your home page
        {
            "request": request, 
            "posts": posts, 
            "notifications": notifications, 
            "current_user": current_user
        }
    )

# API routes
@app.get("/post", response_model=List[schemas.PostResponse])
async def get_posts(request: Request, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    posts = crud.get_posts(db, user_id=current_user.id)
    return templates.TemplateResponse("posts.html", {"request": request, "current_user": current_user, "posts": posts})


@app.post("/post", response_model=schemas.PostResponse)
async def create_post(
        request: Request,
        post_content: str = Form(...),
        file: UploadFile = File(None),  # Optional file
        current_user: models.User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    # Initialize file_url as None
    file_url = None

    # Check if a file is provided before attempting to upload
    if file and file.filename:  # Ensure file exists and has a name
        file_url = upload_file_to_minio(file)  # Upload file to MinIO and get the URL

    post_data = schemas.PostCreate(content=post_content)
    new_post = crud.create_post(db, post_data, user_id=current_user.id, file_url=file_url)

    notification = schemas.NotificationCreate(
        user_id=current_user.id,
        post_id=new_post.id,
        message=f'{current_user.first_name} uploaded a post'
    )
    crud.create_notification(db, notification, user_id=current_user.id)

    return RedirectResponse("/", status_code=303)


@app.api_route("/logout", methods=["GET", "POST"])
async def logout(request: Request):
    response = RedirectResponse(url="/signin")
    response.delete_cookie(key="access_token")  # Clear the access token cookie
    return response


@app.get("/notifications/json", response_model=List[schemas.NotificationResponse])
async def get_unseen_notifications_json(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Query unseen notifications for the current user, excluding those they created
    notifications = db.query(models.Notification)\
        .filter(models.Notification.user_id != current_user.id, models.Notification.seen == False)\
        .order_by(models.Notification.timestamp.desc())\
        .all()
    return notifications


@app.put("/notifications/mark-seen")
async def mark_notifications_seen(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    crud.mark_notifications_as_seen(db, current_user.id)
    return {"status": "success"}

