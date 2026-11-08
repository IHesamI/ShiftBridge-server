"""Database seeding script for ShiftBridge.

Creates:
- 1 Manager user
- 15 Worker users
- 1 Project with the manager and all 15 workers assigned
- Initial scheduled shifts for workers across upcoming days
"""

import sys
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session

from database import engine, SessionLocal, Base
import models
import security

WORKERS_DATA = [
    {"email": "worker1@shiftbridge.com", "full_name": "Alex Morgan"},
    {"email": "worker2@shiftbridge.com", "full_name": "Brian Davis"},
    {"email": "worker3@shiftbridge.com", "full_name": "Chloe Bennett"},
    {"email": "worker4@shiftbridge.com", "full_name": "David Miller"},
    {"email": "worker5@shiftbridge.com", "full_name": "Elena Rostova"},
    {"email": "worker6@shiftbridge.com", "full_name": "Felix Vance"},
    {"email": "worker7@shiftbridge.com", "full_name": "Grace Hopper"},
    {"email": "worker8@shiftbridge.com", "full_name": "Hector Santos"},
    {"email": "worker9@shiftbridge.com", "full_name": "Iris Chen"},
    {"email": "worker10@shiftbridge.com", "full_name": "James Wilson"},
    {"email": "worker11@shiftbridge.com", "full_name": "Kavita Patel"},
    {"email": "worker12@shiftbridge.com", "full_name": "Liam O'Connor"},
    {"email": "worker13@shiftbridge.com", "full_name": "Maya Lin"},
    {"email": "worker14@shiftbridge.com", "full_name": "Noah Taylor"},
    {"email": "worker15@shiftbridge.com", "full_name": "Olivia Martinez"},
]

MANAGER_DATA = {
    "email": "manager@shiftbridge.com",
    "full_name": "Sarah Connor (Project Manager)"
}

PROJECT_TITLE = "Metropolis Skyline Project"
DEFAULT_PASSWORD = "password123"


def seed_database(db: Optional[Session] = None, reset: bool = False):
    """Seed the database with 1 manager, 15 workers, 1 project, and shifts."""
    owns_session = False
    if db is None:
        db = SessionLocal()
        owns_session = True

    try:
        # Ensure all tables exist
        Base.metadata.create_all(bind=engine)

        if reset:
            print("Resetting database tables...")
            db.query(models.Shift).delete()
            db.execute(models.project_workers.delete())
            db.query(models.Project).delete()
            # Delete only seeded test users to preserve custom users if any
            emails_to_delete = [w["email"] for w in WORKERS_DATA] + [MANAGER_DATA["email"]]
            db.query(models.User).filter(models.User.email.in_(emails_to_delete)).delete(synchronize_session=False)
            db.commit()

        # 1. Create or get Manager
        manager = db.query(models.User).filter(models.User.email == MANAGER_DATA["email"]).first()
        if not manager:
            manager = models.User(
                email=MANAGER_DATA["email"],
                hashed_password=security.get_password_hash(DEFAULT_PASSWORD),
                full_name=MANAGER_DATA["full_name"],
                is_active=True
            )
            db.add(manager)
            db.commit()
            db.refresh(manager)
            print(f"Created Manager: {manager.full_name} ({manager.email}) [ID: {manager.id}]")
        else:
            print(f"Manager already exists: {manager.email} [ID: {manager.id}]")

        # 2. Create or get 15 Workers
        workers = []
        for w_data in WORKERS_DATA:
            worker = db.query(models.User).filter(models.User.email == w_data["email"]).first()
            if not worker:
                worker = models.User(
                    email=w_data["email"],
                    hashed_password=security.get_password_hash(DEFAULT_PASSWORD),
                    full_name=w_data["full_name"],
                    is_active=True
                )
                db.add(worker)
                db.commit()
                db.refresh(worker)
                print(f"Created Worker: {worker.full_name} ({worker.email}) [ID: {worker.id}]")
            else:
                print(f"Worker already exists: {worker.email} [ID: {worker.id}]")
            workers.append(worker)

        # 3. Create or get Project with the Manager and all 15 Workers
        project = db.query(models.Project).filter(models.Project.title == PROJECT_TITLE).first()
        if not project:
            project = models.Project(
                manager_id=manager.id,
                title=PROJECT_TITLE,
                workers=workers
            )
            db.add(project)
            db.commit()
            db.refresh(project)
            print(f"\nCreated Project: '{project.title}' [ID: {project.id}]")
            print(f"  Manager ID: {project.manager_id} ({manager.full_name})")
            print(f"  Assigned Workers: {len(project.workers)} workers")
        else:
            # Ensure all 15 workers are linked to this project
            existing_worker_ids = {w.id for w in project.workers}
            for w in workers:
                if w.id not in existing_worker_ids:
                    project.workers.append(w)
            project.manager_id = manager.id
            db.commit()
            db.refresh(project)
            print(f"\nProject '{project.title}' already exists [ID: {project.id}] with {len(project.workers)} workers.")

        # 4. Create sample upcoming shifts for the workers
        now = datetime.now()
        shifts_created = 0
        for i, worker in enumerate(workers):
            # Check if this worker already has a shift in this project
            existing_shift = db.query(models.Shift).filter(
                models.Shift.project_id == project.id,
                models.Shift.owner_id == worker.id
            ).first()

            if not existing_shift:
                # Stagger shifts across upcoming days and hours
                day_offset = (i % 5) + 1  # 1 to 5 days from now
                start_hour = 8 if i % 2 == 0 else 16  # morning (8am) or evening (4pm)
                shift_date = (now + timedelta(days=day_offset)).replace(
                    hour=start_hour, minute=0, second=0, microsecond=0
                )
                shift = models.Shift(
                    project_id=project.id,
                    owner_id=worker.id,
                    start_date=shift_date,
                    length=8
                )
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
        print(f"Project: {project.title} (ID: {project.id})")
        print(f"Manager: {manager.email} | Password: {DEFAULT_PASSWORD}")
        print(f"Workers: {len(workers)} users created/assigned | Default Password: {DEFAULT_PASSWORD}")
        print("=" * 60)

        return {
            "manager_id": manager.id,
            "project_id": project.id,
            "workers_count": len(workers),
            "shifts_created": shifts_created
        }

    finally:
        if owns_session:
            db.close()


if __name__ == "__main__":
    should_reset = "--reset" in sys.argv
    seed_database(reset=should_reset)
