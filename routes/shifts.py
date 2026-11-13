
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from database import get_db
from routes.auth import get_current_user
import models
import schemas

router = APIRouter(prefix="/data", tags=["Data Models Retrieval"])

@router.get("/projects", response_model=List[schemas.ProjectResponse],)
def get_projects(db: Session = Depends(get_db)):
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
                current_user = Depends(get_current_user)
                ):
    """Retrieve all seeded workers."""
    return db.query(models.Worker).all()

@router.get("/shifts", response_model=List[schemas.ShiftResponse])
def get_all_shifts(project_id: Optional[str] = None, db: Session = Depends(get_db),):
    """Retrieve all scheduled shifts, optionally filtered by project ID."""
    query = db.query(models.Shift)
    if project_id:
        query = query.filter(models.Shift.project_id == project_id)
    return query.all()

@router.get("/scenarios", response_model=List[schemas.ScenarioResponse],)
def get_scenarios(db: Session = Depends(get_db), ):
    """Retrieve all scheduling conflict scenarios."""
    return db.query(models.Scenario).all()

@router.get("/proposals", response_model=List[schemas.ProposalResponse])
def get_proposals(db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    """Retrieve proposals for workers or for managers overseeing workers with worker details."""
    # Check if the current user is a manager
    manager = db.query(models.Manager).filter(models.Manager.id == current_user.id).first()
    if manager:
        # Retrieve all worker IDs belonging to projects managed by this manager
        worker_ids = db.query(models.Worker.id).join(models.project_workers).join(models.Project).filter(models.Project.manager_id == manager.id).distinct().all()
        worker_id_list = [w[0] for w in worker_ids]
        proposals = db.query(models.Proposal).filter(models.Proposal.worker_id.in_(worker_id_list)).all()
    else:
        # Fallback to returning proposals specific to the logged-in worker
        proposals = db.query(models.Proposal).filter(models.Proposal.worker_id == current_user.id).all()

    # Map proposals to include worker name and email
    response_data = []
    for proposal in proposals:
        proposal_dict = {
            "id": proposal.id,
            "worker_id": proposal.worker_id,
            "new_shift_data": proposal.new_shift_data,
            "isManagerApproved": proposal.isManagerApproved,
            "isWorkerApproved": proposal.isWorkerApproved,
            "worker_name": proposal.worker.name if proposal.worker else None,
            "worker_email": proposal.worker.email if proposal.worker else None,
        }
        response_data.append(proposal_dict)

    return response_data


@router.post("/approve")
def approve_proposal(
    payload: schemas.ProposalApprovalRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Approve a proposal as either the assigned worker or the supervising manager."""
    proposal = db.query(models.Proposal).filter(models.Proposal.id == payload.proposal_id).first()
    if not proposal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proposal not found")
    
    # Check if current_user is the worker who owns the proposal
    if proposal.worker_id == current_user.id:
        proposal.isWorkerApproved = True
    else:
        # Verify if current_user is a manager supervising the worker associated with this proposal
        is_manager_of_worker = db.query(models.Project).join(models.project_workers).filter(
            models.Project.manager_id == current_user.id,
            models.project_workers.c.worker_id == proposal.worker_id
        ).first() is not None or db.query(models.Manager).filter(models.Manager.id == current_user.id).first() is not None
        
        if is_manager_of_worker:
            proposal.isManagerApproved = True
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to approve this proposal"
            )
            
    # Check if both worker and manager have approved
    if proposal.isWorkerApproved and proposal.isManagerApproved:
        if proposal.new_shift_data:
            shift_data = dict(proposal.new_shift_data)
            if "worker_id" not in shift_data:
                shift_data["worker_id"] = proposal.worker_id
            new_shift = models.Shift(**shift_data)
            db.add(new_shift)
        
        db.delete(proposal)
        db.commit()
        return {"success": True, "message": "Proposal fully approved, new shift created, and proposal deleted."}
    else:
        db.commit()
        db.refresh(proposal)
        return proposal