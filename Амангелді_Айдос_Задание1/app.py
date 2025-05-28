from typing import List
from fastapi import FastAPI, Depends
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, Integer, String, DateTime, select
from datetime import datetime
from pydantic import BaseModel



DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost/notes_db"

engine = create_async_engine(DATABASE_URL, echo=True, future=True)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

Base = declarative_base()

class Note(Base):
    __tablename__ = "notes"

    id = Column(Integer, primary_key=True, index=True)
    text = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


async def get_session() -> AsyncSession:
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()

app = FastAPI(title='Notes API')

@app.on_event('startup')
async def startap():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@app.get('/')
async def root():
    return {"meassage": "success"}


class NoteCreate(BaseModel):
    text: str

class NoteOut(BaseModel):
    id: int
    text: str
    created_at: datetime

    class Config:
        from_attributes = True


@app.post("/notes", response_model=NoteOut)
async def create_note(note: NoteCreate, session: AsyncSession=Depends(get_session)):
    db_note = Note(text=note.text)

    session.add(db_note)
    await session.commit()
    await session.refresh(db_note)

    return db_note


@app.get("/notes", response_model=List[NoteOut])
async def get_notes(session: AsyncSession=Depends(get_session)):
    query = select(Note).order_by(Note.created_at.desc())
    res = await session.execute(query)

    notes = res.scalars().all()

    return notes