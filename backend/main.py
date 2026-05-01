from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel
from core.database import get_db
from core.security import create_access_token, get_current_user, verify_password, get_password_hash
from models.user import User

app = FastAPI(
    title="GCC Audit SaaS API",
    description="Backend API for the local audit agent and compliance tools.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict this to frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from routers.hierarchy import router as hierarchy_router
from routers.audit import router as audit_router
from routers.memory import router as memory_router
from routers.schemes import router as schemes_router
from routers.scheduler import router as scheduler_router
from routers.standards import router as standards_router
from routers.settings import router as settings_router

@app.get("/")
def read_root():
    return {"message": "Welcome to the GCC Audit SaaS API"}

app.include_router(hierarchy_router)
app.include_router(audit_router)
app.include_router(memory_router)
app.include_router(schemes_router)
app.include_router(scheduler_router)
app.include_router(standards_router)
app.include_router(settings_router)

@app.get("/health")
def health_check():
    return {"status": "healthy"}

class UserRegisterRequest(BaseModel):
    email: str
    password: str
    company_id: int

@app.post("/users/register")
async def register_user(user_data: UserRegisterRequest, db: Session = Depends(get_db)):
    """Register a new user"""
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Create new user
    hashed_password = get_password_hash(user_data.password)
    new_user = User(
        email=user_data.email,
        hashed_password=hashed_password,
        company_id=user_data.company_id,
        is_active=True
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {
        "message": "User registered successfully",
        "user_id": new_user.id,
        "email": new_user.email
    }

@app.post("/token")
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Login endpoint - returns JWT token"""
    try:
        # Query user from database
        user = db.query(User).filter(User.email == form_data.username).first()
        if not user:
            raise HTTPException(status_code=401, detail="Incorrect email or password")

        # Verify password
        if not verify_password(form_data.password, user.hashed_password):
            raise HTTPException(status_code=401, detail="Incorrect email or password")

        if not user.is_active:
            raise HTTPException(status_code=403, detail="User account is disabled")

        access_token = create_access_token(data={"sub": user.email})
        return {"access_token": access_token, "token_type": "bearer"}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Login error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Login error: {str(e)}")

@app.get("/users/me")
async def read_users_me(current_user: dict = Depends(get_current_user)):
    return {"user": current_user, "message": "You have successfully accessed a secured endpoint!"}

