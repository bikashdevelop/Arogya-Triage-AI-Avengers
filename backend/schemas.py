from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any   # 👈 ADDED Any


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    full_name: str


class Vitals(BaseModel):
    bp_systolic: int
    bp_diastolic: int
    heart_rate: int
    spo2: int
    temperature_f: float
    respiratory_rate: int


class PatientInput(BaseModel):
    patient_id: str
    abha_id: Optional[str] = ""
    age: int
    sex: str
    name: str
    mobile: Optional[str] = None
    email: Optional[str] = None
    category: Optional[str] = "None"
    duration: Optional[str] = None
    severity: Optional[str] = None
    medical_history: Optional[str] = None
    allergies: Optional[str] = None
    current_medications: Optional[str] = None
    pregnancy_status: Optional[str] = None
    consent_given: bool = False


# 👈 UPDATED: TriageRequest now accepts all fields sent by the frontend
class TriageRequest(BaseModel):
    patient: PatientInput
    symptoms_text: str
    vitals: Vitals
    facility_type: str = "PHC"
    original_transcript: Optional[str] = None
    translated_text: Optional[str] = None
    symptom_onset: Optional[str] = None
    lab_findings: Optional[Dict[str, Any]] = None
    followup_answers: Optional[Dict[str, Any]] = None
    followup_questions: Optional[List[Dict[str, Any]]] = None
    image_findings: Optional[str] = None
    lab_extracted: Optional[Dict[str, Any]] = None
    image_observations: Optional[Dict[str, Any]] = None


class FollowUpAnswersRequest(BaseModel):
    answers: Dict[str, str]


class DecisionRequest(BaseModel):
    decision: str = Field("approve", pattern="^(approve|override)$")
    final_priority: str = Field("P3", pattern="^(P1|P2|P3|P4)$")
    clinical_notes: str = ""
    action: str = Field("opd", pattern="^(admit|refer|opd)$")
    assigned_department: Optional[str] = None
    assigned_doctor_id: Optional[int] = None


class MedicineItem(BaseModel):
    name: str
    dosage: Optional[str] = None
    frequency: Optional[str] = None
    duration: Optional[str] = None
    instructions: Optional[str] = None


class DoctorDecisionWithMeds(BaseModel):
    patient_id: int
    token: Optional[str] = None
    doctor_name: Optional[str] = None
    decision: str = "approve"
    final_priority: str = Field("P3", pattern="^(P1|P2|P3|P4)$")
    action: str = "Send to OPD"
    clinical_notes: str = ""
    medicines: List[MedicineItem] = []


class DispensedItem(BaseModel):
    name: str
    quantity: Optional[str] = None
    notes: Optional[str] = None


class ChemistDispenseInput(BaseModel):
    token: str
    chemist_name: str
    dispensed_items: List[DispensedItem] = []
    out_of_stock_items: List[str] = []