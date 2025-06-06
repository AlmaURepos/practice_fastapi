from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from database import User, get_session, create_tables
from .utils import get_pass_hash, verify_pass
from .auth import create_access_token

class UserCreate(BaseModel):
    username: str
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class UserResponse(BaseModel):
    id: int
    username: str

class Token(BaseModel):
    access_token: str
    token_type: str



app = FastAPI(title='Auth API')


@app.on_event('startup')
async def startap():
    await create_tables()


@app.get('/')
async def root():
    return {"meassage": "success"}


@app.post("/register", response_model=UserResponse)
async def register_user(user: UserCreate, session: AsyncSession= Depends(get_session)):
    query = select(User).where(User.username == user.username)
    res = await session.execute(query)
    existing_user = res.scalar_one_or_none()
    if existing_user:
        raise HTTPException(status_code=400, detail=f"User {user.username} is already existing!")
    
    hashed_pass = get_pass_hash(user.password)
    db_user = User(username= user.username, password=hashed_pass)
    session.add(db_user)
    await session.commit()
    await session.refresh(db_user)
    return db_user


@app.post("/login")
async def login_user(user: UserLogin, session: AsyncSession= Depends(get_session)):
    query = select(User).where(User.username == user.username)
    res = await session.execute(query)
    db_user = res.scalar_one_or_none()
    if not db_user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    if not verify_pass(user.password, db_user.password):
        raise HTTPException(status_code=401, detail="Invalid access data")
    
    access_token = create_access_token(data={"sub": db_user.username})
    
    # return {"msg": "Success", "username": db_user.username}
    return Token(access_token=access_token, token_type="bearer")




