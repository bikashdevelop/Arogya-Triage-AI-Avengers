from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from datetime import datetime
from database import Base


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    department = Column(String, nullable=True)
    facility_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Patient(Base):
    __tablename__ = "patients"
    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(String, index=True)
    abha_id = Column(String)
    age = Column(Integer)
    sex = Column(String)
    name = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)


class TriageRecord(Base):
    __tablename__ = "triage_records"
    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"))
    facility_id = Column(String, nullable=True)
    symptoms_text = Column(String)
    vitals_json = Column(String)
    mews_score = Column(Integer, default=0)
    ai_priority = Column(String, default="P3")
    final_priority = Column(String, nullable=True)
    doctor_decision = Column(String, default="pending")
    clinical_notes = Column(String, default="")
    ai_summary = Column(String, default="")
    ai_timeline_json = Column(String, default="[]")
    ai_gaps_json = Column(String, default="[]")
    ai_questions_json = Column(String, default="[]")
    ai_source = Column(String, default="unknown")
    status = Column(String, default="Waiting Review")
    assigned_department = Column(String, nullable=True)
    assigned_doctor_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    claimed_at = Column(DateTime, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"))
    reviewed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    reviewed_at = Column(DateTime, nullable=True)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    record_id = Column(Integer, nullable=True)
    action = Column(String)
    details = Column(String, default="")
    timestamp = Column(DateTime, default=datetime.utcnow)