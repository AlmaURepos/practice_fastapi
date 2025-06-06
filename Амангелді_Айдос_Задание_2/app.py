from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from database import User, get_session, create_tables

class UserCreate(BaseModel):
    username: str
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class UserResponse(BaseModel):
    id: int
    username: str



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
    
    db_user = User(username= user.username, password=user.password)
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
    
    if db_user.password != user.password:
        raise HTTPException(status_code=401, detail="Invalid access data")
    
    return {"msg": "Success", "username": db_user.username}




