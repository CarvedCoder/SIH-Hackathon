from sqlalchemy import create_engine, Column, String, Float, Integer, DateTime, JSON, Text
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker
import pytz
from datetime import datetime
# Database Configuration
DATABASE_URL = "sqlite:///./backend/data/database/citizen_reporter.db"
engine = create_engine(
    DATABASE_URL, 
    connect_args={"check_same_thread": False}  #only for sqlite
)
IST = pytz.timezone('Asia/Kolkata')

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class HazardReport(Base):
    __tablename__ = "hazard_reports"
    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False)
    timestamp = Column(DateTime, default= lambda: datetime.now(IST))
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    location_name = Column(String)
    hazard_type = Column(String, nullable=False)
    severity = Column(Integer)  # 1-5 scale
    description = Column(Text)
    media_urls = Column(JSON)
    verification_status = Column(String, default="pending")  
    priority_score = Column(Float)
    nearby_reports = Column(JSON)  # IDs of reports within 5km
    weather_conditions = Column(JSON)
    
Base.metadata.create_all(bind=engine)

class AuthorityAlerts(Base):
    __tablename__= "authority_alerts"
    id = Column(String, primary_key=True)
    report_id = Column(String, nullable=False)
    authority_type = Column(String,nullable=False)
    message = Column(String,nullable=False)
    status =  Column(String,nullable=False)
    timestamp = Column(DateTime, default= lambda: datetime.now(IST))

Base.metadata.create_all(bind=engine)


