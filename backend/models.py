# backend/models.py
from sqlalchemy import Column, Integer, String, Text, create_engine, Index, UniqueConstraint
from sqlalchemy.orm import declarative_base, sessionmaker
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///tierlist.db")

# Convert SQLite URL to PostgreSQL if needed for production
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL, echo=False, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()

class TierSave(Base):
    __tablename__ = "tier_saves"
    id = Column(Integer, primary_key=True)
    user = Column(String(200), nullable=False)
    playlist_id = Column(String(64), nullable=False)
    data_json = Column(Text, nullable=False)

    __table_args__ = (
        Index("ix_user_playlist", "user", "playlist_id"),
        UniqueConstraint("user", "playlist_id", name="uq_user_playlist"),
    )

def init_db():
    Base.metadata.create_all(bind=engine)
