import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from backend.database import Base


class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    description = Column(Text, nullable=False)
    status = Column(String(20), default="pending")  # pending, expanding, queued, generating, completed, failed
    total_images = Column(Integer, default=0)
    completed_images = Column(Integer, default=0)
    source_photo = Column(String(255), default="colin_face3.jpg")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    error_message = Column(Text, nullable=True)

    images = relationship("GeneratedImage", back_populates="job", cascade="all, delete-orphan")


class GeneratedImage(Base):
    __tablename__ = "generated_images"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False)
    filename = Column(String(255), nullable=False)
    positive_prompt = Column(Text, nullable=False)
    negative_prompt = Column(Text, nullable=True)
    scene_description = Column(String(500), nullable=True)
    seed = Column(Integer, nullable=True)
    width = Column(Integer, default=1024)
    height = Column(Integer, default=1024)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    job = relationship("Job", back_populates="images")
