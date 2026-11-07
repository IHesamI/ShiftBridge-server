from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Table
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base

# Association table for Many-to-Many relationship between Projects and Workers (Users)
project_workers = Table(
    "project_workers",
    Base.metadata,
    Column("project_id", Integer, ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True),
    Column("user_id", Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
)

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)

    # Relationships
    managed_projects = relationship("Project", back_populates="manager", foreign_keys="Project.manager_id")
    projects = relationship("Project", secondary=project_workers, back_populates="workers")
    shifts = relationship("Shift", back_populates="owner", foreign_keys="Shift.owner_id")

class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    manager_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.now)

    # Relationships
    manager = relationship("User", foreign_keys=[manager_id], back_populates="managed_projects")
    workers = relationship("User", secondary=project_workers, back_populates="projects")
    shifts = relationship("Shift", back_populates="project", cascade="all, delete-orphan")

class Shift(Base):
    __tablename__ = "shifts"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    start_date = Column(DateTime, nullable=False)
    length = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.now)

    # Relationships
    project = relationship("Project", back_populates="shifts")
    owner = relationship("User", foreign_keys=[owner_id], back_populates="shifts")