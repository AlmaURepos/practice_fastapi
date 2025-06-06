from datetime import datetime
from typing import List
from fastapi import FastAPI, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database import Note, get_session, create_tables



class NoteCreate(BaseModel):
    text: str

class NoteOut(BaseModel):
    id: int
    text: str
    created_at: datetime

    class Config:
        from_attributes = True

app = FastAPI(title='Notes API')


@app.on_event('startup')
async def startap():
    await create_tables()


@app.get('/')
async def root():
    return {"meassage": "success"}


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