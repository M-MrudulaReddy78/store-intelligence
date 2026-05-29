from sqlalchemy import create_engine, Column, String, DateTime, Integer, Float, Boolean, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./store_intelligence.db")
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class EventRecord(Base):
    __tablename__ = "events"
    event_id = Column(String, primary_key=True, index=True)
    store_id = Column(String, index=True)
    camera_id = Column(String)
    visitor_id = Column(String, index=True)
    event_type = Column(String)
    timestamp = Column(DateTime, index=True)
    zone_id = Column(String, nullable=True)
    dwell_ms = Column(Integer)
    is_staff = Column(Boolean)
    confidence = Column(Float)
    metadata_json = Column(JSON)

class SessionRecord(Base):
    __tablename__ = "sessions"
    visitor_id = Column(String, primary_key=True)
    store_id = Column(String, index=True)
    entry_time = Column(DateTime)
    exit_time = Column(DateTime, nullable=True)
    converted = Column(Boolean, default=False)

class POSTransaction(Base):
    __tablename__ = "pos_transactions"
    id = Column(Integer, primary_key=True, autoincrement=True)
    store_id = Column(String, index=True)
    transaction_id = Column(String, unique=True)
    timestamp = Column(DateTime, index=True)
    basket_value_inr = Column(Float)

Base.metadata.create_all(bind=engine)