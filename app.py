import logging
from fastapi import FastAPI, Request
from pydantic import BaseModel
import datetime

# --- Configure Logging ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(_name_)

app = FastAPI(title="EduLink Backend PoC",
              description="Proof of Concept for Automated Deployment with Docker + Bunny.net Magic Containers",
              version="1.0")

# --- Simulated Database ---
students = []

class Student(BaseModel):
    id: int
    name: str
    enrolled_class: str
    date_joined: datetime.date

# --- Middleware for request logging ---
@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"Incoming request: {request.method} {request.url}")
    response = await call_next(request)
    logger.info(f"Response status: {response.status_code} for {request.method} {request.url}")
    return response

# --- API Endpoints ---
@app.get("/")
def root():
    logger.info("Root endpoint accessed")
    return {"message": "EduLink Backend is running - Deployed via Docker & Magic Containers!"}

@app.get("/students")
def get_students():
    logger.info("Fetching list of students")
    return {"students": students}

@app.post("/students")
def add_student(student: Student):
    students.append(student.dict())
    logger.info(f"Added new student: {student.name} (ID: {student.id})")
    return {"message": "Student added successfully!", "student": student}

@app.get("/health")
def health_check():
    logger.info("Health check requested")
    return {"status": "healthy", "timestamp": datetime.datetime.now()}