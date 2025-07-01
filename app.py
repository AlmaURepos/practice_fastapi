from datetime import datetime
from typing import List, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException, status, Query, APIRouter, WebSocket, WebSocketDisconnect
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic_settings import BaseSettings

from database import Note, User, get_session, create_tables
from depends import get_current_user, require_role
from utils import get_pass_hash, verify_pass
from auth import create_access_token
from celery_config import app as celery_app
from config import settings
from logging_config import setup_logging
import redis.asyncio as redis
import json
import logging
import time
from prometheus_fastapi_instrumentator import Instrumentator
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from sqlalchemy.exc import SQLAlchemyError
from starlette.types import ASGIApp, Receive, Scope, Send

app = FastAPI(
    title="Notes + Auth API",
    description="""
A modern API for user authentication and note management. Features include JWT-based authentication, user roles, rate limiting, and real-time updates via WebSocket. All endpoints are grouped and documented for clarity.
""",
    version="1.0.0",
    contact={
        "name": "Aidos Amangeldy",
        "email": "amangeldiaidos660@gmail.com",
        "url": "https://github.com/amangeldiaidos660"
    }
)
router = APIRouter()
setup_logging()

# redis_client = redis.from_url(settings.redis_url, decode_responses=True)
def get_redis_client():
    return redis.from_url(settings.redis_url, decode_responses=True)


# --- MODELS ---

class ErrorResponse(BaseModel):
    detail: str = Field(..., description="Error message", example="User already exists")

class UserCreate(BaseModel):
    username: str = Field(..., description="Unique username", example="johndoe")
    password: str = Field(..., description="User password", example="strongpassword123")

class UserLogin(BaseModel):
    username: str = Field(..., description="Unique username", example="johndoe")
    password: str = Field(..., description="User password", example="strongpassword123")

class UserResponse(BaseModel):
    id: int = Field(..., description="User ID", example=1)
    username: str = Field(..., description="Unique username", example="johndoe")

class Token(BaseModel):
    access_token: str = Field(..., description="JWT access token", example="eyJhbGciOiJIUzI1NiIsInR5cCI6...")
    token_type: str = Field(..., description="Token type", example="bearer")

class NoteCreate(BaseModel):
    text: str = Field(..., description="Note text", example="Buy milk")

class NoteOut(BaseModel):
    id: int = Field(..., description="Note ID", example=1)
    text: str = Field(..., description="Note text", example="Buy milk")
    created_at: datetime = Field(..., description="Creation timestamp", example="2024-06-01T12:00:00Z")
    owner_id: int = Field(..., description="Owner user ID", example=1)

    class Config:
        from_attributes = True

class NoteUpdate(BaseModel):
    text: str = Field(..., description="Updated note text", example="Buy bread")

# WebSocket
class ConnectionManager:
    def __init__(self):
        self.active_conn: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_conn.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_conn.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_conn:
            await connection.send_text(message)

manager = ConnectionManager()

# --- STARTUP ---

@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_tables()
    yield

app.lifespan = lifespan

# --- COMMON ---

@app.get("/")
async def root():
    return {"message": "success"}

# --- AUTH ENDPOINTS ---

@app.post(
    "/register",
    response_model=UserResponse,
    tags=["Authentication"],
    summary="Register a new user",
    description="Creates a new user with a unique username. Returns the created user's data.",
    responses={
        200: {"description": "User successfully created", "model": UserResponse, "content": {"application/json": {"example": {"id": 1, "username": "johndoe"}}}},
        400: {"description": "User already exists", "model": ErrorResponse, "content": {"application/json": {"example": {"detail": "User johndoe already exists"}}}},
    },
)
async def register_user(user: UserCreate, session: AsyncSession = Depends(get_session)):
    logger = logging.getLogger("app.request")
    query = select(User).where(User.username == user.username)
    res = await session.execute(query)
    existing_user = res.scalar_one_or_none()
    if existing_user:
        logger.warning("", extra={"username": user.username, "reason": "already exists"})
        raise HTTPException(status_code=400, detail=f"User {user.username} already exists")
    hashed_pass = get_pass_hash(user.password)
    db_user = User(username=user.username, password=hashed_pass)
    session.add(db_user)
    await session.commit()
    await session.refresh(db_user)
    logger.info("", extra={"username": user.username, "user_id": db_user.id})
    return db_user

@app.post(
    "/login",
    response_model=Token,
    tags=["Authentication"],
    summary="User login",
    description="Authenticates a user and returns a JWT access token.",
    responses={
        200: {"description": "Successful login", "model": Token, "content": {"application/json": {"example": {"access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6...", "token_type": "bearer"}}}},
        401: {"description": "Invalid credentials", "model": ErrorResponse, "content": {"application/json": {"example": {"detail": "Invalid username or password"}}}},
    },
)
async def login_user(user: UserLogin, session: AsyncSession = Depends(get_session)):
    logger = logging.getLogger("app.request")
    query = select(User).where(User.username == user.username)
    res = await session.execute(query)
    db_user = res.scalar_one_or_none()
    if not db_user or not verify_pass(user.password, db_user.password):
        logger.warning("", extra={"username": user.username})
        raise HTTPException(status_code=401, detail="Invalid username or password")
    access_token = create_access_token(data={"sub": db_user.username})
    logger.info("", extra={"username": user.username, "user_id": db_user.id})
    return Token(access_token=access_token, token_type="bearer")

@app.get(
    "/users/me",
    response_model=UserResponse,
    tags=["Authentication"],
    summary="Get current user info",
    description="Returns the authenticated user's information.",
    responses={
        200: {"description": "Current user info", "model": UserResponse, "content": {"application/json": {"example": {"id": 1, "username": "johndoe"}}}},
        401: {"description": "Not authenticated", "model": ErrorResponse, "content": {"application/json": {"example": {"detail": "Not authenticated"}}}},
    },
)
async def get_me(current_user: User = Depends(get_current_user)):
    return {"id": current_user.id, "username": current_user.username}

@app.get(
    "/admin/users",
    response_model=List[UserResponse],
    tags=["Admin"],
    summary="Get all users (admin only)",
    description="Returns a list of all users. Only accessible by admin users.",
    responses={
        200: {"description": "List of users", "content": {"application/json": {"example": [{"id": 1, "username": "johndoe"}, {"id": 2, "username": "alice"}]}}, "model": UserResponse},
        403: {"description": "Permission error", "model": ErrorResponse, "content": {"application/json": {"example": {"detail": "Permission error"}}}},
        401: {"description": "Not authenticated", "model": ErrorResponse, "content": {"application/json": {"example": {"detail": "Not authenticated"}}}},
    },
)
async def get_all_users(
    current_user: User = Depends(require_role('admin')),
    session: AsyncSession = Depends(get_session)
):
    query = select(User)
    res = await session.execute(query)
    users = res.scalars().all()
    return [{"id": user.id, "username": user.username} for user in users]

# --- NOTES ENDPOINTS ---

@app.post(
    "/notes",
    response_model=NoteOut,
    tags=["Notes"],
    summary="Create a new note",
    description="Creates a new note for the authenticated user.",
    responses={
        200: {"description": "Note created", "model": NoteOut, "content": {"application/json": {"example": {"id": 1, "text": "Buy milk", "created_at": "2024-06-01T12:00:00Z", "owner_id": 1}}}},
        401: {"description": "Not authenticated", "model": ErrorResponse, "content": {"application/json": {"example": {"detail": "Not authenticated"}}}},
    },
)
async def create_note(
    note: NoteCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    redis_client = get_redis_client()
    db_note = Note(text=note.text, owner_id=current_user.id)
    session.add(db_note)
    await session.commit()
    await session.refresh(db_note)
    keys = [key async for key in redis_client.scan_iter(f"notes:{current_user.id}:*")]
    if keys:
        await redis_client.delete(*keys)

    return db_note

@app.get(
    "/notes",
    response_model=List[NoteOut],
    tags=["Notes"],
    summary="Get all notes",
    description="Returns a list of notes for the authenticated user. Supports pagination and search.",
    responses={
        200: {"description": "List of notes", "content": {"application/json": {"example": [{"id": 1, "text": "Buy milk", "created_at": "2024-06-01T12:00:00Z", "owner_id": 1}]}}},
        401: {"description": "Not authenticated", "model": ErrorResponse, "content": {"application/json": {"example": {"detail": "Not authenticated"}}}},
    },
)
async def get_notes(
    skip: int = Query(0, ge=0, description="Number of items to skip", example=0),
    limit: int = Query(100, ge=1, description="Maximum number of items to return", example=10),
    search: Optional[str] = Query(None, min_length=1, description="Search query for note text", example="milk"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    redis_client = get_redis_client()
    cache_key = f"notes:{current_user.id}:{skip}:{limit}:{search or ''}"
    cached_data = await redis_client.get(cache_key)
    if cached_data:
        return json.loads(cached_data)
    query = select(Note).where(Note.owner_id == current_user.id)
    if search:
        query = query.where(Note.text.ilike(f"%{search}%"))
    query = query.order_by(Note.created_at.desc()).offset(skip).limit(limit)
    res = await session.execute(query)
    notes = res.scalars().all()

    # serialized_notes = [note.dict() for note in notes]
    
    # await redis_client.setex(cache_key, 600, json.dumps(serialized_notes))
    
    serialized_notes = [NoteOut.from_orm(note).dict() for note in notes]
    await redis_client.setex(cache_key, 600, json.dumps(serialized_notes, default=str))
    return notes

@app.get(
    "/notes/{note_id}",
    response_model=NoteOut,
    tags=["Notes"],
    summary="Get note by ID",
    description="Returns a note by its ID for the authenticated user.",
    responses={
        200: {"description": "Note found", "model": NoteOut, "content": {"application/json": {"example": {"id": 1, "text": "Buy milk", "created_at": "2024-06-01T12:00:00Z", "owner_id": 1}}}},
        404: {"description": "Note not found or access denied", "model": ErrorResponse, "content": {"application/json": {"example": {"detail": "Note not found or access denied"}}}},
        401: {"description": "Not authenticated", "model": ErrorResponse, "content": {"application/json": {"example": {"detail": "Not authenticated"}}}},
    },
)
async def get_note_by_id(
    note_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    query = select(Note).where(Note.id == note_id, Note.owner_id == current_user.id)
    res = await session.execute(query)
    note = res.scalar_one_or_none()
    if note is None:
        raise HTTPException(status_code=404, detail="Note not found or access denied")
    return note

@app.put(
    "/notes/{note_id}",
    response_model=NoteOut,
    tags=["Notes"],
    summary="Update a note",
    description="Updates a note by its ID for the authenticated user.",
    responses={
        200: {"description": "Note updated", "model": NoteOut, "content": {"application/json": {"example": {"id": 1, "text": "Buy bread", "created_at": "2024-06-01T12:00:00Z", "owner_id": 1}}}},
        404: {"description": "Note not found or access denied", "model": ErrorResponse, "content": {"application/json": {"example": {"detail": "Note not found or access denied"}}}},
        401: {"description": "Not authenticated", "model": ErrorResponse, "content": {"application/json": {"example": {"detail": "Not authenticated"}}}},
    },
)
async def update_note(
    note_id: int,
    note_update: NoteUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    redis_client = get_redis_client()
    query = select(Note).where(Note.id == note_id, Note.owner_id == current_user.id)
    res = await session.execute(query)
    note = res.scalar_one_or_none()
    if note is None:
        raise HTTPException(status_code=404, detail="Note not found or access denied")
    note.text = note_update.text
    await session.commit()
    await session.refresh(note)
    await redis_client.delete([key async for key in redis_client.scan_iter(f"notes:{current_user.id}:*")])
    return note

@app.delete(
    "/notes/{note_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Notes"],
    summary="Delete a note",
    description="Deletes a note by its ID for the authenticated user.",
    responses={
        204: {"description": "Note deleted"},
        404: {"description": "Note not found or access denied", "model": ErrorResponse, "content": {"application/json": {"example": {"detail": "Note not found or access denied"}}}},
        401: {"description": "Not authenticated", "model": ErrorResponse, "content": {"application/json": {"example": {"detail": "Not authenticated"}}}},
    },
)
async def delete_note(
    note_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    redis_client = get_redis_client()
    query = select(Note).where(Note.id == note_id, Note.owner_id == current_user.id)
    res = await session.execute(query)
    note = res.scalar_one_or_none()
    if note is None:
        raise HTTPException(status_code=404, detail="Note not found or access denied")
    await session.delete(note)
    await session.commit()
    # await redis_client.delete([key async for key in redis_client.scan_iter(f"notes:{current_user.id}:*")])
    keys = [key async for key in redis_client.scan_iter(f"notes:{current_user.id}:*")]
    if keys:
        await redis_client.delete(*keys)

    return {"message": "Note deleted"}

# --- CELERY ENDPOINT ---

@router.post(
    "/trigger-task",
    status_code=status.HTTP_202_ACCEPTED,
    tags=["Admin"],
    summary="Trigger background task",
    description="Triggers a background Celery task. Only for demonstration.",
    responses={
        202: {"description": "Task started", "content": {"application/json": {"example": {"message": "Task started"}}}},
        401: {"description": "Not authenticated", "model": ErrorResponse, "content": {"application/json": {"example": {"detail": "Not authenticated"}}}},
    },
)
async def trigger_task(current_user: User = Depends(get_current_user)):
    celery_app.send_task('tasks.send_mock_msg')
    return {"message": "Task started"}

app.include_router(router)

# --- WEB SOCKET ---

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, current_user: User = Depends(get_current_user)):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await manager.broadcast(f"User {current_user.username}: {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        await manager.broadcast(f"User {current_user.username} disconnected")
    except Exception as e:
        manager.disconnect(websocket)
        await websocket.close()

class RateLimiterMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, redis_url: str, limit: int, window: int):
        super().__init__(app)
        self.redis_url = redis_url
        self.limit = limit
        self.window = window

    async def get_redis(self):
        return redis.from_url(self.redis_url, decode_responses=True)

    async def dispatch(self, request: Request, call_next):
        # Создаём redis-клиента внутри запроса
        redis_client = await self.get_redis()
        try:
            key = f"rate_limit:{request.client.host}"
            count = await redis_client.incr(key)
            if count == 1:
                await redis_client.expire(key, self.window)
            if count > self.limit:
                return Response("Too Many Requests", status_code=429)
            response = await call_next(request)
            return response
        finally:
            await redis_client.close()

class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        logger = logging.getLogger("app.request")
        start_time = time.time()
        response = await call_next(request)
        process_time = (time.time() - start_time) * 1000
        logger.info(
            "",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "process_time_ms": round(process_time, 2)
            }
        )
        return response

app.add_middleware(
    RateLimiterMiddleware,
    redis_url=settings.redis_url,
    limit=settings.rate_limit,
    window=settings.rate_limit_window
)
app.add_middleware(LoggingMiddleware)

@app.get(
    "/health",
    tags=["Health"],
    summary="Health check",
    description="Checks if the service and database are available.",
    responses={
        200: {"description": "Service is healthy", "content": {"application/json": {"example": {"status": "ok"}}}},
        503: {"description": "Service unavailable", "model": ErrorResponse, "content": {"application/json": {"example": {"detail": "Service Unavailable"}}}},
    },
)
async def health(session: AsyncSession = Depends(get_session)):
    try:
        await session.execute(select(1))
        return {"status": "ok"}
    except SQLAlchemyError:
        raise HTTPException(status_code=503, detail="Service Unavailable")

Instrumentator().instrument(app).expose(app)