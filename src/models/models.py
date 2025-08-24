# src/pasa/models.py
from sqlalchemy import Column, String, Text, DateTime
from src.db.database import Base

class JobPost(Base):
    __tablename__ = "job_posts"
    job_id = Column(String, primary_key=True, index=True)
    timestamp = Column(DateTime)
    sender = Column(String, index=True)
    message = Column(Text)
    status = Column(String, default="new")
