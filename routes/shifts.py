
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from database import get_db
from routes.auth import get_current_user
import models
import schemas

router = APIRouter(prefix="/data", tags=["Data Models Retrieval"])

@router.get("/projects", response_model=List[schemas.ProjectResponse])
def get_projects(db: Session = Depends(get_db), ):
    """Retrieve all projects including assigned workers and manager details."""
    projects = db.query(models.Project).all()
    return projects

@router.get("/projects/{project_id}", response_model=schemas.ProjectResponse)
def get_project_by_id(project_id: str, db: Session = Depends(get_db), ):
    """Retrieve a specific project by its ID."""
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project

@router.get("/workers", response_model=List[schemas.WorkerResponse])
def get_workers(db: Session = Depends(get_db), 
                # current_user = Depends(get_current_user)
                ):
    """Retrieve all seeded workers."""
    return db.query(models.Worker).all()

@router.get("/shifts", response_model=List[schemas.ShiftResponse])
def get_all_shifts(project_id: Optional[str] = None, db: Session = Depends(get_db)):
    """Retrieve all scheduled shifts, optionally filtered by project ID."""
    query = db.query(models.Shift)
    if project_id:
        query = query.filter(models.Shift.project_id == project_id)
    return query.all()

@router.get("/scenarios", response_model=List[schemas.ScenarioResponse])
def get_scenarios(db: Session = Depends(get_db), ):
    """Retrieve all scheduling conflict scenarios."""
    return db.query(models.Scenario).all()

@router.get("/proposals", response_model=List[schemas.ChatMessageResponse])
def get_chat_messages(db: Session = Depends(get_db), ):
    """Retrieve all chat messages, options, and proposal/approval states."""
    return db.query(models.ChatMessage).all()