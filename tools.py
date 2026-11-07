from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from dateutil import parser as date_parser
import models

# Tool definitions metadata (compatible with OpenAI/Gemini/local function calling standards)
AVAILABLE_TOOLS = [
    {
        "name": "get_other_workers_shifts",
        "description": "Fetch shifts of other workers/coworkers in the specified project to check their schedules, availability, and avoid conflicts.",
        "parameters": {
            "type": "object",
            "properties": {
                "project_id": {
                    "type": "integer",
                    "description": "The ID of the project. If not provided, coworkers' shifts across all user's projects will be retrieved."
                }
            },
            "required": []
        }
    },
    {
        "name": "get_my_shifts",
        "description": "Fetch the current user's scheduled shifts.",
        "parameters": {
            "type": "object",
            "properties": {
                "project_id": {
                    "type": "integer",
                    "description": "Optional project ID to filter user's shifts."
                }
            },
            "required": []
        }
    },
    {
        "name": "reschedule_shift",
        "description": "Change/reschedule an existing shift of the current user to a new start date and time, and optionally change its length.",
        "parameters": {
            "type": "object",
            "properties": {
                "shift_id": {
                    "type": "integer",
                    "description": "The ID of the shift to reschedule. If omitted and the user has a single shift, that shift is selected."
                },
                "new_start_date": {
                    "type": "string",
                    "description": "The new start date and time (e.g. '2026-11-10T09:00:00' or '2026-11-10 09:00')."
                },
                "new_length": {
                    "type": "integer",
                    "description": "Optional new duration/length of the shift in hours."
                }
            },
            "required": ["new_start_date"]
        }
    }
]

# OpenAI-compatible function calling tool schemas
OPENAI_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": t["name"],
            "description": t["description"],
            "parameters": t["parameters"]
        }
    }
    for t in AVAILABLE_TOOLS
]


def tool_get_other_workers_shifts(
    db: Session,
    current_user_id: int,
    project_id: Optional[int] = None
) -> Dict[str, Any]:
    """Retrieve other workers' shifts for a project or all projects the user is involved in."""
    # Find projects the user is associated with
    query = db.query(models.Shift).filter(models.Shift.owner_id != current_user_id)
    
    if project_id is not None:
        query = query.filter(models.Shift.project_id == project_id)
    else:
        # Get projects where current user is manager or worker
        user = db.query(models.User).filter(models.User.id == current_user_id).first()
        if user:
            user_project_ids = [p.id for p in user.projects]
            managed_ids = [p.id for p in user.managed_projects]
            all_project_ids = list(set(user_project_ids + managed_ids))
            if all_project_ids:
                query = query.filter(models.Shift.project_id.in_(all_project_ids))

    shifts = query.order_by(models.Shift.start_date.asc()).all()
    
    results = []
    for s in shifts:
        owner_name = s.owner.full_name or s.owner.email if s.owner else "Unknown"
        project_title = s.project.title if s.project else "Unknown"
        results.append({
            "shift_id": s.id,
            "project_id": s.project_id,
            "project_title": project_title,
            "worker_id": s.owner_id,
            "worker_name": owner_name,
            "worker_email": s.owner.email if s.owner else "",
            "start_date": s.start_date.isoformat(),
            "length": s.length
        })
        
    return {
        "success": True,
        "count": len(results),
        "shifts": results
    }


def tool_get_my_shifts(
    db: Session,
    current_user_id: int,
    project_id: Optional[int] = None
) -> Dict[str, Any]:
    """Retrieve all shifts belonging to the current user."""
    query = db.query(models.Shift).filter(models.Shift.owner_id == current_user_id)
    if project_id is not None:
        query = query.filter(models.Shift.project_id == project_id)
        
    shifts = query.order_by(models.Shift.start_date.asc()).all()
    results = []
    for s in shifts:
        project_title = s.project.title if s.project else "Unknown"
        results.append({
            "shift_id": s.id,
            "project_id": s.project_id,
            "project_title": project_title,
            "start_date": s.start_date.isoformat(),
            "length": s.length
        })
        
    return {
        "success": True,
        "count": len(results),
        "shifts": results
    }


def tool_reschedule_shift(
    db: Session,
    current_user_id: int,
    new_start_date: str,
    shift_id: Optional[int] = None,
    new_length: Optional[int] = None
) -> Dict[str, Any]:
    """Reschedule the current user's shift to a new start date/time and optionally new length."""
    # Find shift
    if shift_id is not None:
        shift = db.query(models.Shift).filter(
            models.Shift.id == shift_id,
            models.Shift.owner_id == current_user_id
        ).first()
        if not shift:
            return {
                "success": False,
                "error": f"Shift with ID {shift_id} not found or does not belong to you."
            }
    else:
        # Try to automatically pick user's shift if there's only one
        user_shifts = db.query(models.Shift).filter(
            models.Shift.owner_id == current_user_id
        ).order_by(models.Shift.start_date.asc()).all()
        
        if not user_shifts:
            return {
                "success": False,
                "error": "No shifts found for you to reschedule."
            }
        elif len(user_shifts) == 1:
            shift = user_shifts[0]
        else:
            return {
                "success": False,
                "error": f"You have multiple shifts ({len(user_shifts)}). Please specify the shift_id you want to reschedule.",
                "available_shifts": [
                    {"shift_id": s.id, "project_id": s.project_id, "start_date": s.start_date.isoformat(), "length": s.length}
                    for s in user_shifts
                ]
            }

    # Parse date
    try:
        parsed_date = date_parser.parse(new_start_date)
    except Exception as e:
        return {
            "success": False,
            "error": f"Could not parse date '{new_start_date}'. Please provide a valid date format (e.g. YYYY-MM-DD HH:MM)."
        }

    old_start = shift.start_date.isoformat()
    old_length = shift.length

    shift.start_date = parsed_date
    if new_length is not None and new_length > 0:
        shift.length = new_length

    db.commit()
    db.refresh(shift)

    return {
        "success": True,
        "message": f"Successfully rescheduled shift #{shift.id}.",
        "shift": {
            "shift_id": shift.id,
            "project_id": shift.project_id,
            "project_title": shift.project.title if shift.project else "Unknown",
            "previous_start_date": old_start,
            "new_start_date": shift.start_date.isoformat(),
            "previous_length": old_length,
            "new_length": shift.length
        }
    }


def execute_tool_by_name(
    tool_name: str,
    args: Dict[str, Any],
    db: Session,
    current_user_id: int
) -> Dict[str, Any]:
    """Execute a tool by name with arguments."""
    if tool_name == "get_other_workers_shifts":
        project_id = args.get("project_id")
        return tool_get_other_workers_shifts(db, current_user_id, project_id=project_id)
    elif tool_name == "get_my_shifts":
        project_id = args.get("project_id")
        return tool_get_my_shifts(db, current_user_id, project_id=project_id)
    elif tool_name == "reschedule_shift":
        return tool_reschedule_shift(
            db=db,
            current_user_id=current_user_id,
            new_start_date=args.get("new_start_date", ""),
            shift_id=args.get("shift_id"),
            new_length=args.get("new_length")
        )
    else:
        return {
            "success": False,
            "error": f"Unknown tool: '{tool_name}'"
        }
