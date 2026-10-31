from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from .database import get_db
from .models import Task, User, RefreshToken

from .auth import hash_password, verify_password, create_access_token, verify_access_token, create_refresh_token, hash_refresh_token

from .schemas import TaskResponse, TaskCreate, TaskUpdate, UserCreate, UserLogin, TokenResponse, RefreshTokenRequest, LogoutRequest
import uuid
app = FastAPI()

# current user dependency (Authentication functionality)
security = HTTPBearer()

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    token = credentials.credentials

    user_id = verify_access_token(token)

    if user_id is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token"
        )

    current_user = db.query(User).filter(
        User.id == int(user_id)
    ).first()

    if current_user is None:
        raise HTTPException(
            status_code=401,
            detail="User not found"
        )

    return current_user

# test endpoint
@app.get("/auth/me")
def get_my_profile(
    current_user: User = Depends(get_current_user)
):
    return {
        "id": current_user.id,
        "email": current_user.email
    }


#register user endpoint
@app.post("/auth/register", status_code=201)
def register(user: UserCreate, db:Session =Depends(get_db)):
    existing_user=db.query(User).filter(User.email==user.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed_password= hash_password(user.password)
    new_user=User(email=user.email, password_hash=hashed_password)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"message": "User registered successfully",  "user": {
        "id": new_user.id,
        "email": new_user.email
    }}

#login endpoint
@app.post("/auth/login", response_model=TokenResponse)
def login_user(user: UserLogin, db: Session = Depends(get_db)):

    existing_user = db.query(User).filter(
        User.email == user.email
    ).first()

    if not existing_user or not verify_password(
        user.password, existing_user.password_hash
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"}
        )

    # Generate access token
    access_token = create_access_token(existing_user.id)

    # Generate refresh token
    refresh_token = create_refresh_token()

    # Hash refresh token before storing it
    token_hash = hash_refresh_token(refresh_token)

    # Calculate refresh token expiry
    expires_at = datetime.now(timezone.utc) + timedelta(days=7)
    family_id = uuid.uuid4()  # Generate a unique family ID for this refresh token  
    # Store refresh token in database
    new_refresh_token = RefreshToken(
        user_id=existing_user.id,
        token_hash=token_hash,
        expires_at=expires_at,
        family_id=family_id
    )

    db.add(new_refresh_token)
    db.commit()

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }

#logout endpoint
@app.post("/auth/logout")
def logout_user(
    request: LogoutRequest,
    db: Session = Depends(get_db)
):
    # Hash the incoming refresh token
    token_hash = hash_refresh_token(request.refresh_token)

    # Find the token in the database
    stored_token = db.query(RefreshToken).filter(
        RefreshToken.token_hash == token_hash
    ).first()

    # Check if token exists
    if stored_token is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid refresh token"
        )

    # Check if already revoked
    if stored_token.revoked_at is not None:
        raise HTTPException(
            status_code=401,
            detail="Refresh token already revoked"
        )

    # Revoke the token
    stored_token.revoked_at = datetime.now(timezone.utc)
    db.commit()
    return {"message": "Successfully logged out"}



@app.get("/")
def home():
    return {"message": "AI Task Manager API"}


#task endpoints

from fastapi import Query

@app.get("/tasks", response_model=list[TaskResponse])
def get_tasks(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    sort_by: str = Query("due_date"),
    order: str = Query("asc"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Task).filter(
        Task.user_id == current_user.id
    )

    # Allowed sorting options
    if sort_by == "due_date":
        column = Task.due_date
    elif sort_by == "created_at":
        column = Task.created_at
    elif sort_by == "priority":
        column = Task.priority
    else:
        column = Task.due_date

    # Sorting order
    if order == "desc":
        query = query.order_by(column.desc())
    else:
        query = query.order_by(column.asc())

    # Pagination
    offset = (page - 1) * limit

    tasks = query.offset(offset).limit(limit).all()

    return tasks

@app.post("/tasks", response_model=TaskResponse, status_code=201)
def create_task(task: TaskCreate, db:Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    new_task= Task(
        user_id=current_user.id,
        title=task.title,
        description=task.description,
        priority=task.priority,
        due_date=task.due_date
    )
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    return new_task

@app.get("/tasks/{task_id}", response_model=TaskResponse)
def get_task(task_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    task = db.query(Task).filter(Task.id == task_id).first()
    
    # Combined check: returns 404 if task doesn't exist OR belongs to another user
    if not task or task.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Task not found")
        
    return task

@app.patch("/tasks/{task_id}", response_model=TaskResponse, status_code=200)
def update_task(task_id: int, task: TaskUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    existing_task = db.query(Task).filter(Task.id == task_id).first()
    
    # Combined check: returns 404 if task doesn't exist OR belongs to another user
    if existing_task is None or existing_task.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Task not found")

    update_data = task.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(existing_task, key, value)
    db.commit()
    db.refresh(existing_task)
    return existing_task

@app.delete("/tasks/{task_id}", status_code=204)
def delete_task(task_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    task = db.query(Task).filter(Task.id == task_id).first()
    
    # Added ownership validation: returns 404 if task doesn't exist OR belongs to another user
    if not task or task.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Task not found")
        
    db.delete(task)
    db.commit()
    return {"message": "Task deleted successfully"}


@app.post("/auth/refresh", response_model=TokenResponse)
def refresh_access_token(
    request: RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    # 1. Hash the incoming refresh token
    token_hash = hash_refresh_token(request.refresh_token)

    # 2. Find the token in the database
    stored_token = db.query(RefreshToken).filter(
        RefreshToken.token_hash == token_hash
    ).first()

    # 3. Validate token existence
    if stored_token is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid refresh token"
        )

    # 4. Detect refresh-token reuse
    if stored_token.revoked_at is not None:

        # Revoke every active token in this family
        db.query(RefreshToken).filter(
            RefreshToken.family_id == stored_token.family_id,
            RefreshToken.revoked_at.is_(None)
        ).update(
            {"revoked_at": datetime.now(timezone.utc)},
            synchronize_session=False
        )

        db.commit()

        raise HTTPException(
            status_code=401,
            detail="Refresh token reuse detected. Please log in again."
        )

    # 5. Check expiry
    expires_at = stored_token.expires_at

    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if expires_at <= datetime.now(timezone.utc):
        raise HTTPException(
            status_code=401,
            detail="Refresh token has expired"
        )

    # 6. Find the user
    user = db.query(User).filter(
        User.id == stored_token.user_id
    ).first()

    if user is None:
        raise HTTPException(
            status_code=401,
            detail="User not found"
        )

    # 7. Generate new tokens
    new_access_token = create_access_token(user.id)
    new_refresh_token = create_refresh_token()

    # 8. Revoke old token
    stored_token.revoked_at = datetime.now(timezone.utc)

    # 9. Create new token in the SAME family
    new_stored_token = RefreshToken(
        user_id=user.id,
        token_hash=hash_refresh_token(new_refresh_token),
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        family_id=stored_token.family_id
    )

    db.add(new_stored_token)

    # Get the new token's database ID
    db.flush()

    # Link old token to its replacement
    stored_token.replaced_by_id = new_stored_token.id

    # 10. Commit everything
    db.commit()

    # 11. Return new tokens
    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer"
    }