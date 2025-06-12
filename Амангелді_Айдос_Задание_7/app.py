from datetime import datetime
from typing import List
from fastapi import FastAPI, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database import Note, User, get_session, create_tables
from .depends import get_current_user



class NoteCreate(BaseModel):
    text: str

class NoteOut(BaseModel):
    id: int
    text: str
    created_at: datetime
    owner_id: int

    class Config:
        from_attributes = True

class NoteUpdate(BaseModel):
    text: str

app = FastAPI(title='Notes API')


@app.on_event('startup')
async def startap():
    await create_tables()


@app.get('/')
async def root():
    return {"meassage": "success"}


@app.post("/notes", response_model=NoteOut)
async def create_note(note: NoteCreate, current_user: User=Depends(get_current_user), session: AsyncSession=Depends(get_session)):
    db_note = Note(text=note.text, owner_id=current_user.id)

    session.add(db_note)
    await session.commit()
    await session.refresh(db_note)

    return db_note


@app.get("/notes", response_model=List[NoteOut])
async def get_notes(current_user: User=Depends(get_current_user), session: AsyncSession=Depends(get_session)):
    query = select(Note).where(Note.owner_id==current_user.id).order_by(Note.created_at.desc())
    res = await session.execute(query)

    notes = res.scalars().all()

    return notes


@app.get("/notes/{node_id}", response_model=NoteOut)
async def get_note_by_id(node_id: int, current_user: User=Depends(get_current_user), session: AsyncSession=Depends(get_session)):
    query = select(Note).where(Note.id==node_id, Note.owner_id==current_user.id)
    res = await session.execute(query)
    note = res.scalar_one_or_none()

    if note is None:
        raise HTTPException(status_code=404, detail="Note is not found or access error")

    return note


@app.put("/notes/{node_id}", response_model=NoteOut)
async def update_note(node_id: int, note_update: NoteUpdate, current_user: User=Depends(get_current_user), session: AsyncSession=Depends(get_session)):
    query = select(Note).where(Note.id==node_id, Note.owner_id==current_user.id)
    res = await session.execute(query)

    note = res.scalar_one_or_none()
    if note is None:
        raise HTTPException(status_code=404, detail="Note is not found or access error")
    
    note.text = note_update.text
    await session.commit()
    await session.refresh(note)

    return note

@app.delete("/notes/{node_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_note(node_id: int, current_user: User=Depends(get_current_user), session: AsyncSession=Depends(get_session)):
    query = select(Note).where(Note.id==node_id, Note.owner_id==current_user.id)
    res = await session.execute(query)

    note = res.scalar_one_or_none()
    if note is None:
        raise HTTPException(status_code=404, detail="Note is not found or access error")
    
    await session.delete(note)
    await session.commit()

    return {"message": "Note is deleted"}