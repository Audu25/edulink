import os
import logging
import datetime
from typing import Annotated, AsyncGenerator, List, Optional

from fastapi import FastAPI, Request, Depends, HTTPException, status
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy import Date, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy import select, delete

# --- Configure Logging ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="EduLink Backend PoC",
    description="Proof of Concept for Automated Deployment with Docker + Bunny.net Magic Containers",
    version="1.1"
)

# --- Settings / Env ---
# Example: postgresql+asyncpg://postgres:postgres@db:5432/edulink
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://myuser:mypassword@edulink-postgres:5432/mydatabase"
)

# --- SQLAlchemy Setup (Async) ---
class Base(DeclarativeBase):
    pass

class StudentORM(Base):
    __tablename__ = "students"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    enrolled_class: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    date_joined: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(default=func.now(), server_default=func.now(), nullable=False)

# Async engine & session factory
engine = create_async_engine(DATABASE_URL, echo=False, pool_pre_ping=True)
SessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False, autocommit=False)

async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session

DbDep = Annotated[AsyncSession, Depends(get_session)]

# --- Pydantic Schemas ---
class StudentIn(BaseModel):
    id: int = Field(..., ge=1)
    name: str = Field(..., min_length=1, max_length=200)
    enrolled_class: str = Field(..., min_length=1, max_length=120)
    date_joined: datetime.date  # ISO date like "2025-08-17"

class StudentOut(StudentIn):
    model_config = ConfigDict(from_attributes=True)
    created_at: datetime.datetime

# --- Middleware for request logging ---
@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info("Incoming request: %s %s", request.method, request.url)
    response = await call_next(request)
    logger.info("Response status: %s for %s %s", response.status_code, request.method, request.url)
    return response

# --- Lifespan: create tables on startup ---
@app.on_event("startup")
async def on_startup():
    logger.info("Starting up and ensuring database schema exists...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database schema ready.")

# --- API Endpoints ---
@app.get("/")
async def root():
    logger.info("Root endpoint accessed")
    return {"message": "EduLink Backend is running now version 2 - Deployed via Docker & Magic Containers (DB-backed)!"}

@app.get("/students", response_model=dict)
async def get_students(db: DbDep):
    logger.info("Fetching list of students from DB")
    result = await db.execute(select(StudentORM).order_by(StudentORM.id))
    items: List[StudentORM] = result.scalars().all()
    return {"students": [StudentOut.model_validate(i) for i in items]}

@app.get("/students/{student_id}", response_model=StudentOut)
async def get_student(student_id: int, db: DbDep):
    logger.info("Fetching student id=%s", student_id)
    result = await db.execute(select(StudentORM).where(StudentORM.id == student_id))
    student: Optional[StudentORM] = result.scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")
    return StudentOut.model_validate(student)

@app.post("/students", response_model=dict, status_code=status.HTTP_201_CREATED)
async def add_student(student: StudentIn, db: DbDep):
    logger.info("Adding new student: %s (ID: %s)", student.name, student.id)
    # avoid duplicate primary key
    existing = await db.execute(select(StudentORM).where(StudentORM.id == student.id))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Student with this ID already exists")

    obj = StudentORM(
        id=student.id,
        name=student.name,
        enrolled_class=student.enrolled_class,
        date_joined=student.date_joined,
    )
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return {"message": "Student added successfully!", "student": StudentOut.model_validate(obj)}

@app.delete("/students/{student_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_student(student_id: int, db: DbDep):
    logger.info("Deleting student id=%s", student_id)
    result = await db.execute(select(StudentORM).where(StudentORM.id == student_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")
    await db.execute(delete(StudentORM).where(StudentORM.id == student_id))
    await db.commit()
    return None

@app.get("/health")
async def health_check(db: DbDep):
    logger.info("Health check requested")
    # Verify DB connectivity with a lightweight query
    try:
        await db.execute(select(func.now()))
        db_ok = True
    except Exception as e:
        logger.exception("DB health check failed: %s", e)
        db_ok = False
    return {
        "status": "healthy" if db_ok else "degraded",
        "db": "ok" if db_ok else "error",
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }

