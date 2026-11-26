"""Database seeding script for ShiftBridge.

Creates:
- 1 Manager worker (with is_manager=True)
- 15 Workers with specific emails, roles, departments, avatars, and hour metrics
- 3 Projects with the manager worker and workers assigned via association table
- Initial scheduled shifts for workers across days of the week, including
  2 shifts for worker1 across two different projects
"""
import random
import sys
from typing import Optional
from sqlalchemy.orm import Session

from database import engine, SessionLocal, Base
import models
import security
def random_generator(lower=1000,upper=100000):
    return random.uniform(lower, upper)
WORKERS_DATA = [
    {"id": "w1", "email": "worker1@shiftbridge.com", "name": "Alex Morgan", "role": "Senior RN", "department": "Emergency", "max_hours": 40.0, "current_hours": 32.0, "avatar": "https://api.dicebear.com/7.x/avataaars/svg?seed=Alex", "is_manager": False},
    {"id": "w2", "email": "worker2@shiftbridge.com", "name": "Brian Davis", "role": "RN", "department": "ICU", "max_hours": 40.0, "current_hours": 36.0, "avatar": "https://api.dicebear.com/7.x/avataaars/svg?seed=Brian", "is_manager": False},
    {"id": "w3", "email": "worker3@shiftbridge.com", "name": "Chloe Bennett", "role": "Charge Nurse", "department": "Emergency", "max_hours": 40.0, "current_hours": 40.0, "avatar": "https://api.dicebear.com/7.x/avataaars/svg?seed=Chloe", "is_manager": False},
    {"id": "w4", "email": "worker4@shiftbridge.com", "name": "David Miller", "role": "LPN", "department": "Pediatrics", "max_hours": 36.0, "current_hours": 24.0, "avatar": "https://api.dicebear.com/7.x/avataaars/svg?seed=David", "is_manager": False},
    {"id": "w5", "email": "worker5@shiftbridge.com", "name": "Elena Rostova", "role": "RN", "department": "Surgery", "max_hours": 40.0, "current_hours": 38.0, "avatar": "https://api.dicebear.com/7.x/avataaars/svg?seed=Elena", "is_manager": False},
    {"id": "w6", "email": "worker6@shiftbridge.com", "name": "Felix Vance", "role": "Support Specialist", "department": "General", "max_hours": 30.0, "current_hours": 20.0, "avatar": "https://api.dicebear.com/7.x/avataaars/svg?seed=Felix", "is_manager": False},
    {"id": "w7", "email": "worker7@shiftbridge.com", "name": "Grace Hopper", "role": "Senior RN", "department": "ICU", "max_hours": 40.0, "current_hours": 40.0, "avatar": "https://api.dicebear.com/7.x/avataaars/svg?seed=Grace", "is_manager": False},
    {"id": "w8", "email": "worker8@shiftbridge.com", "name": "Hector Santos", "role": "RN", "department": "Pediatrics", "max_hours": 40.0, "current_hours": 32.0, "avatar": "https://api.dicebear.com/7.x/avataaars/svg?seed=Hector", "is_manager": False},
    {"id": "w9", "email": "worker9@shiftbridge.com", "name": "Iris Chen", "role": "Charge Nurse", "department": "Surgery", "max_hours": 40.0, "current_hours": 36.0, "avatar": "https://api.dicebear.com/7.x/avataaars/svg?seed=Iris", "is_manager": False},
    {"id": "w10", "email": "worker10@shiftbridge.com", "name": "James Wilson", "role": "LPN", "department": "Emergency", "max_hours": 36.0, "current_hours": 28.0, "avatar": "https://api.dicebear.com/7.x/avataaars/svg?seed=James", "is_manager": False},
    {"id": "w11", "email": "worker11@shiftbridge.com", "name": "Kavita Patel", "role": "RN", "department": "General", "max_hours": 40.0, "current_hours": 34.0, "avatar": "https://api.dicebear.com/7.x/avataaars/svg?seed=Kavita", "is_manager": False},
    {"id": "w12", "email": "worker12@shiftbridge.com", "name": "Liam O'Connor", "role": "Support Specialist", "department": "ICU", "max_hours": 30.0, "current_hours": 25.0, "avatar": "https://api.dicebear.com/7.x/avataaars/svg?seed=Liam", "is_manager": False},
    {"id": "w13", "email": "worker13@shiftbridge.com", "name": "Maya Lin", "role": "Senior RN", "department": "Pediatrics", "max_hours": 40.0, "current_hours": 38.0, "avatar": "https://api.dicebear.com/7.x/avataaars/svg?seed=Maya", "is_manager": False},
    {"id": "w14", "email": "worker14@shiftbridge.com", "name": "Noah Taylor", "role": "RN", "department": "Emergency", "max_hours": 40.0, "current_hours": 30.0, "avatar": "https://api.dicebear.com/7.x/avataaars/svg?seed=Noah", "is_manager": False},
    {"id": "w15", "email": "worker15@shiftbridge.com", "name": "Olivia Martinez", "role": "LPN", "department": "Surgery", "max_hours": 36.0, "current_hours": 32.0, "avatar": "https://api.dicebear.com/7.x/avataaars/svg?seed=Olivia", "is_manager": False},
]

MANAGER_DATA = {
    "id": "m1",
    "email": "manager@shiftbridge.com",
    "name": "Sarah Connor",
    "role": "Project Manager",
    "department": "Management",
    "max_hours": 40.0,
    "current_hours": 0.0,
    "avatar": "https://api.dicebear.com/7.x/avataaars/svg?seed=Sarah",
    "is_manager": True
}

PROJECTS_DATA = [
    {
        "id": "proj_1",
        "title": "Metropolis Healthcare Scheduling",
        "worker_ids": [w["id"] for w in WORKERS_DATA],
    },
    {
        "id": "proj_2",
        "title": "Critical Care & ICU Rotation",
        "worker_ids": ["w1", "w2", "w3", "w5", "w7", "w9", "w12"],
    },
    {
        "id": "proj_3",
        "title": "Pediatrics & Outpatient Clinic",
        "worker_ids": ["w4", "w6", "w8", "w10", "w11", "w13", "w14", "w15"],
    },
]

DEFAULT_PASSWORD = "password123"
DAYS_OF_WEEK = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def seed_database(db: Optional[Session] = None, reset: bool = False):
    """Seed the database with 1 manager worker, 15 workers, 3 projects, and shifts."""
    owns_session = False
    if db is None:
        db = SessionLocal()
        owns_session = True

    try:
        if reset:
            print("Resetting and dropping database tables...")
            Base.metadata.drop_all(bind=engine)

        # Ensure all tables exist with the latest schema
        Base.metadata.create_all(bind=engine)

        # 1. Create or get Manager (as a Worker with is_manager=True)
        manager = db.query(models.Worker).filter(models.Worker.email == MANAGER_DATA["email"]).first()
        if not manager:
            manager = models.Worker(
                id=MANAGER_DATA["id"],
                email=MANAGER_DATA["email"],
                hashed_password=security.get_password_hash(DEFAULT_PASSWORD),
                name=MANAGER_DATA["name"],
                role=MANAGER_DATA["role"],
                department=MANAGER_DATA["department"],
                max_hours=MANAGER_DATA["max_hours"],
                current_hours=MANAGER_DATA["current_hours"],
                avatar=MANAGER_DATA["avatar"],
                is_manager=True
            )
            db.add(manager)
            db.commit()
            db.refresh(manager)
            print(f"Created Manager Worker: {manager.name} ({manager.email}) [ID: {manager.id}]")
        else:
            manager.is_manager = True
            db.commit()
            print(f"Manager Worker already exists: {manager.email} [ID: {manager.id}]")

        # 2. Create or get 15 regular Workers
        workers_by_id = {}
        workers = []
        for w_data in WORKERS_DATA:
            worker = db.query(models.Worker).filter(models.Worker.id == w_data["id"]).first()
            if not worker:
                worker = models.Worker(
                    id=w_data["id"],
                    email=w_data["email"],
                    hashed_password=security.get_password_hash(DEFAULT_PASSWORD),
                    name=w_data["name"],
                    role=w_data["role"],
                    department=w_data["department"],
                    max_hours=w_data["max_hours"],
                    current_hours=w_data["current_hours"],
                    avatar=w_data["avatar"],
                    is_manager=False
                )
                db.add(worker)
                db.commit()
                db.refresh(worker)
                print(f"Created Worker: {worker.name} ({worker.role}) [ID: {worker.id}]")
            else:
                worker.is_manager = False
                db.commit()
                print(f"Worker already exists: {worker.name} [ID: {worker.id}]")
            workers.append(worker)
            workers_by_id[worker.id] = worker

        # 3. Create or get 3 Projects with the Manager and assigned Workers
        projects = []
        for p_data in PROJECTS_DATA:
            assigned_workers = [workers_by_id[wid] for wid in p_data["worker_ids"] if wid in workers_by_id]
            project = db.query(models.Project).filter(models.Project.id == p_data["id"]).first()
            if not project:
                project = models.Project(
                    id=p_data["id"],
                    manager_id=manager.id,
                    title=p_data["title"],
                    workers=assigned_workers
                )
                db.add(project)
                db.commit()
                db.refresh(project)
                print(f"\nCreated Project: '{project.title}' [ID: {project.id}]")
                print(f"  Manager ID: {project.manager_id} ({manager.name})")
                print(f"  Assigned Workers: {len(project.workers)} workers")
            else:
                existing_worker_ids = {w.id for w in project.workers}
                for w in assigned_workers:
                    if w.id not in existing_worker_ids:
                        project.workers.append(w)
                project.manager_id = manager.id
                db.commit()
                db.refresh(project)
                print(f"\nProject '{project.title}' already exists [ID: {project.id}] with {len(project.workers)} workers.")
            projects.append(project)

        # 4. Create sample shifts across projects, ensuring worker1 (w1) has 2 shifts in 2 projects
        shifts_created = 0
        monday_id=random_generator()
        wednesday_id=random_generator()
        shifts_to_seed = [
            # Two shifts for target worker w1 across proj_1 and proj_2
            {
                "id": f"shift_w1_proj_1_{monday_id}",
                "project_id": "proj_1",
                "worker_id": "w1",
                "day": "Monday",
                "type": "regular",
                "start_time": "07:00",
                "length": 8.0,
                "note": "Primary hospital schedule shift",
                "updated_by_ai": False,
                "conflict_reason": "",
            },
            {
                "id": f"shift_w1_proj_2_{wednesday_id}",
                "project_id": "proj_2",
                "worker_id": "w1",
                "day": "Wednesday",
                "type": "regular",
                "start_time": "15:00",
                "length": 8.0,
                "note": "ICU rotation shift",
                "updated_by_ai": False,
                "conflict_reason": "",
            },
        ]

        # Seed shifts for remaining workers across projects
        for i, worker in enumerate(workers[1:], start=1):
            day = DAYS_OF_WEEK[i % len(DAYS_OF_WEEK)]
            target_project = projects[i % len(projects)]
            shifts_to_seed.append({
                "id": f"shift_{worker.id}_{target_project.id}_{random_generator()}",
                "project_id": target_project.id,
                "worker_id": worker.id,
                "day": day,
                "type": "regular",
                "start_time": "07:00",
                "length": 8.0,
                "note": "Regular scheduled shift",
                "updated_by_ai": False,
                "conflict_reason": "",
            })

        for s_data in shifts_to_seed:
            existing_shift = db.query(models.Shift).filter(models.Shift.id == s_data["id"]).first()
            if not existing_shift:
                shift = models.Shift(**s_data)
                db.add(shift)
                shifts_created += 1

        if shifts_created > 0:
            db.commit()
            print(f"\nCreated {shifts_created} scheduled shifts for workers.")
        else:
            print("\nShifts already populated.")

        print("\n" + "=" * 60)
        print("SEEDING COMPLETE!")
        print("=" * 60)
        print(f"Projects seeded: {len(projects)} ({', '.join(p.title for p in projects)})")
        print(f"Manager: {manager.email} | Password: {DEFAULT_PASSWORD}")
        print(f"Workers: {len(workers)} workers created/assigned with credentials")
        print("=" * 60)

        return {
            "manager_id": manager.id,
            "project_ids": [p.id for p in projects],
            "workers_count": len(workers),
            "shifts_created": shifts_created
        }

    finally:
        if owns_session:
            db.close()


if __name__ == "__main__":
    should_reset = "--reset" in sys.argv
    seed_database(reset=should_reset)