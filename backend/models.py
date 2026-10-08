from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Text
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
    is_on_duty = Column(Boolean, default=True)
    current_load = Column(Integer, default=0)
    max_load = Column(Integer, default=15)
    years_experience = Column(Integer, default=5)
    total_assigned_today = Column(Integer, default=0)
    avg_consultation_mins = Column(Integer, default=10)


class Patient(Base):
    __tablename__ = "patients"
    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(String, index=True)
    abha_id = Column(String, nullable=True)
    age = Column(Integer, nullable=True)
    sex = Column(String, nullable=True)
    name = Column(String, nullable=True)
    mobile = Column(String, nullable=True)
    email = Column(String, nullable=True)
    category = Column(String, default="None")
    duration_of_symptoms = Column(String, nullable=True)
    severity = Column(String, nullable=True)
    medical_history = Column(String, nullable=True)
    allergies = Column(String, nullable=True)
    current_medications = Column(String, nullable=True)
    pregnancy_status = Column(String, nullable=True)
    consent_given = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class TriageRecord(Base):
    __tablename__ = "triage_records"
    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"))
    facility_id = Column(String, nullable=True)
    symptoms_text = Column(String)
    vitals_json = Column(String)
    original_transcript = Column(Text, nullable=True)
    translated_text = Column(Text, nullable=True)
    mews_score = Column(Integer, default=0)
    ai_priority = Column(String, default="P3")
    final_priority = Column(String, nullable=True)
    ai_summary = Column(Text, default="")
    ai_timeline_json = Column(Text, default="[]")
    ai_gaps_json = Column(Text, default="[]")
    ai_questions_json = Column(Text, default="[]")
    ai_explanation = Column(Text, default="")
    follow_up_answers_json = Column(Text, default="{}")
    priority_window_mins = Column(Integer, default=60)
    is_manually_assigned = Column(Boolean, default=False)
    assigned_department = Column(String, nullable=True)
    assigned_doctor_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    estimated_wait_mins = Column(Integer, default=0)
    doctor_decision = Column(String, default="pending")
    clinical_notes = Column(Text, default="")
    referral_note = Column(Text, nullable=True)
    status = Column(String, default="Waiting Review")
    ai_source = Column(String, default="unknown")
    
    # 👈 NEW COLUMNS ADDED HERE
    lab_extracted_json = Column(Text, default="{}")           # Stores OCR Lab Report data
    image_observations_json = Column(Text, default="{}")      # Stores Vision AI Image data
    
    created_by = Column(Integer, ForeignKey("users.id"))
    reviewed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    reviewed_at = Column(DateTime, nullable=True)


class AssignmentDecision(Base):
    __tablename__ = "assignment_decisions"
    id = Column(Integer, primary_key=True, index=True)
    triage_record_id = Column(Integer, ForeignKey("triage_records.id"), nullable=True)
    chosen_doctor_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    chosen_doctor_name = Column(String, nullable=True)
    chosen_doctor_department = Column(String, nullable=True)
    total_score = Column(Integer, default=0)
    candidates_considered = Column(Integer, default=0)
    reasons_json = Column(Text, default="[]")
    candidate_scores_json = Column(Text, default="[]")
    fallback_used = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    record_id = Column(Integer, nullable=True)
    action = Column(String)
    details = Column(Text, default="")
    timestamp = Column(DateTime, default=datetime.utcnow)


class Facility(Base):
    __tablename__ = "facilities"
    id = Column(Integer, primary_key=True, index=True)
    facility_code = Column(String, unique=True, index=True, nullable=False)
    facility_name = Column(String, nullable=False)
    facility_type = Column(String, nullable=False)
    district = Column(String, nullable=True)
    block = Column(String, nullable=True)
    latitude = Column(String, nullable=True)
    longitude = Column(String, nullable=True)
    emergency_capable = Column(Boolean, default=False)
    operational_status = Column(String, default="open")
    last_verified_at = Column(DateTime, default=datetime.utcnow)
    contact_number = Column(String, nullable=True)


class FacilityCapability(Base):
    __tablename__ = "facility_capabilities"
    id = Column(Integer, primary_key=True, index=True)
    facility_id = Column(Integer, ForeignKey("facilities.id"), nullable=False)
    service_code = Column(String, nullable=False)
    capability_level = Column(String, nullable=False)
    availability_status = Column(String, default="unknown")
    last_verified_at = Column(DateTime, default=datetime.utcnow)
    verification_source = Column(String, default="seed_data")


class ReferralDecision(Base):
    __tablename__ = "referral_decisions"
    id = Column(Integer, primary_key=True, index=True)
    triage_case_id = Column(Integer, ForeignKey("triage_records.id"), nullable=False)
    priority = Column(String, nullable=False)
    suggested_service = Column(String, nullable=False)
    suggested_facility_id = Column(Integer, ForeignKey("facilities.id"), nullable=True)
    suggestion_reasons_json = Column(Text, default="[]")
    routing_confidence = Column(String, default="MEDIUM")
    final_service = Column(String, nullable=True)
    final_facility_id = Column(Integer, ForeignKey("facilities.id"), nullable=True)
    override_flag = Column(Boolean, default=False)
    override_reason = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    finalized_at = Column(DateTime, nullable=True)


class Prescription(Base):
    __tablename__ = "prescriptions"
    id = Column(Integer, primary_key=True, index=True)
    prescription_code = Column(String, unique=True, index=True, nullable=False)
    triage_case_id = Column(Integer, ForeignKey("triage_records.id"), nullable=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    token = Column(String, index=True, nullable=True)
    doctor_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    doctor_name = Column(String, nullable=True)
    medicines_json = Column(Text, default="[]")
    clinical_notes = Column(Text, default="")
    status = Column(String, default="pending")
    chemist_name = Column(String, nullable=True)
    dispensed_items_json = Column(Text, default="[]")
    out_of_stock_items_json = Column(Text, default="[]")
    created_at = Column(DateTime, default=datetime.utcnow)
    dispensed_at = Column(DateTime, nullable=True)


class ICUAdmission(Base):
    __tablename__ = "icu_admissions"
    id = Column(Integer, primary_key=True, index=True)
    triage_case_id = Column(Integer, ForeignKey("triage_records.id"), nullable=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    token = Column(String, index=True, nullable=False)
    priority = Column(String, default="P1")
    notes = Column(Text, default="")
    vitals_history_json = Column(Text, default="[]")
    status = Column(String, default="active")
    admitted_at = Column(DateTime, default=datetime.utcnow)
    discharged_at = Column(DateTime, nullable=True)