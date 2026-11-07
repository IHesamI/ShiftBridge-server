from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from database import get_db
from routes.auth import get_current_user
import models
import schemas
import tools

router = APIRouter(prefix="/shifts", tags=["Shifts"])

@router.get("/my-shifts")
def get_my_shifts(
    project_id: Optional[int] = None,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieve all shifts belonging to the authenticated user."""
    return tools.tool_get_my_shifts(db=db, current_user_id=current_user.id, project_id=project_id)

@router.get("/project/{project_id}/workers")
def get_other_workers_shifts(
    project_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieve shifts of other workers in the project."""
    return tools.tool_get_other_workers_shifts(db=db, current_user_id=current_user.id, project_id=project_id)

@router.patch("/{shift_id}/reschedule")
def reschedule_shift(
    shift_id: int,
    request: schemas.RescheduleRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Directly reschedule an existing shift for the authenticated user."""
    result = tools.tool_reschedule_shift(
        db=db,
        current_user_id=current_user.id,
        new_start_date=request.new_start_date,
        shift_id=shift_id,
        new_length=request.new_length
    )
    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error", "Failed to reschedule shift")
        )
    return result
