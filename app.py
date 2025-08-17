import logging
from fastapi import FastAPI, Request
from pydantic import BaseModel
import datetime

# --- Configure Logging ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="EduLink Backend PoC",
    description="Proof of Concept for Automated Deployment with Docker + Bunny.net Magic Containers",
    version="1.0"
)

# --- Simulated Database ---
students: list[dict] = []

class Student(BaseModel):
    id: int
    name: str
    enrolled_class: str
    date_joined: datetime.date  # expects ISO date like "2025-08-17"

# --- Middleware for request logging ---
@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info("Incoming request: %s %s", request.method, request.url)
    response = await call_next(request)
    logger.info("Response status: %s for %s %s", response.status_code, request.method, request.url)
    return response

# --- API Endpoints ---
@app.get("/")
def root():
    logger.info("Root endpoint accessed")
    return {"message": "EduLink Backend is running now - Deployed via Docker & Magic Containers!"}

@app.get("/students")
def get_students():
    logger.info("Fetching list of students")
    return {"students": students}

@app.post("/students")
def add_student(student: Student):
    # For Pydantic v2 use model_dump(); v1 .dict() also works but is deprecated in v2.
    record = student.model_dump() if hasattr(student, "model_dump") else student.dict()
    students.append(record)
    logger.info("Added new student: %s (ID: %s)", student.name, student.id)
    return {"message": "Student added successfully!", "student": record}

@app.get("/health")
def health_check():
    logger.info("Health check requested")
    return {"status": "healthy", "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()}
