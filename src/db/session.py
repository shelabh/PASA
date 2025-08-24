# src/db/session.py
from sqlmodel import Session, create_engine
import os

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("❌ DATABASE_URL is not set in environment variables.")

# Create engine
engine = create_engine(DATABASE_URL, echo=True)

# Session maker
def get_session():
    with Session(engine) as session:
        yield session
