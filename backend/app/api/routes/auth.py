"""snap3D — Auth Routes"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, EmailStr
from app.core.database import get_db, User
from app.core.auth import hash_password, verify_password, create_access_token, get_current_user

router = APIRouter()

class RegisterBody(BaseModel):
    email: EmailStr; password: str; nickname: str = ""

class TokenResponse(BaseModel):
    access_token: str; token_type: str = "bearer"
    user_id: int; email: str; plan: str

@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(body: RegisterBody, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none(): raise HTTPException(400, "Email already registered")
    user = User(email=body.email, hashed_pw=hash_password(body.password),
        nickname=body.nickname or body.email.split("@")[0])
    db.add(user); await db.commit(); await db.refresh(user)
    token = create_access_token(user.id, user.email)
    return TokenResponse(access_token=token, user_id=user.id, email=user.email, plan=user.plan)

@router.post("/login", response_model=TokenResponse)
async def login(form: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == form.username, User.is_active == True))
    user = result.scalar_one_or_none()
    if not user or not verify_password(form.password, user.hashed_pw):
        raise HTTPException(401, "Incorrect email or password")
    token = create_access_token(user.id, user.email)
    return TokenResponse(access_token=token, user_id=user.id, email=user.email, plan=user.plan)

@router.get("/me")
async def me(user: User = Depends(get_current_user)):
    return {"id": user.id, "email": user.email, "nickname": user.nickname, "plan": user.plan}
