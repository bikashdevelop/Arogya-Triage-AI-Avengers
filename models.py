from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional


# ==========================================
# INPUT MODELS
# ==========================================
class VitalsInput(BaseModel):
    systolic_bp: int = Field(..., description="Systolic Blood Pressure in mmHg")
    diastolic_bp: Optional[int] = Field(None, description="Diastolic Blood Pressure")
    heart_rate: int = Field(..., description="Heart Rate in bpm")
    respiratory_rate: int = Field(..., description="Respiratory Rate in breaths/min")
    temperature_f: float = Field(..., description="Temperature in Fahrenheit")
    spo2: int = Field(..., description="Oxygen Saturation %")


class PatientDataInput(BaseModel):
    demographics: Dict[str, Any] = Field(..., description="Name, age, gender, ABHA ID")
    vitals: VitalsInput
    symptoms: List[str] = Field(..., description="List of extracted symptoms")
    patient_category: Optional[str] = Field("None", description="Pregnancy / Child / None")
    language: Optional[str] = Field("English", description="English / Hindi / Odia")  # ← NEW
    lab_findings: Optional[Dict[str, Any]] = Field(None, description="OCR lab values")
    facility: str = Field("Primary Health Centre (PHC)", description="Current facility type")


# ==========================================
# SUMMARY MODEL
# ==========================================
class SummaryItem(BaseModel):
    info: str
    source: str


# ==========================================
# OUTPUT MODELS
# ==========================================
class RoutingOutput(BaseModel):
    recommended_department: str
    referral_advice: Optional[str] = None
    immediate_checklist: List[str]


class TriageResponse(BaseModel):
    # Core fields
    status: str
    mews_score: int
    mews_breakdown: List[str]
    
    # Patient type (pregnancy/child/adult)
    age_group: Optional[str] = None
    patient_type: Optional[str] = None
    
    # Triage output
    triage_priority: str
    triage_reason: str
    lab_interpretations: Optional[List[str]] = Field(default_factory=list)
    structured_summary: Optional[List[SummaryItem]] = Field(default_factory=list)
    
    # Routing
    routing: RoutingOutput
    
    # Additional info
    identified_missing_info: List[str]
    prioritized_questions: List[str]
    disclaimer: str
    
    # Token & Queue
    token_number: Optional[str] = None
    queue_id: Optional[int] = None
    is_existing_patient: Optional[bool] = Field(False, description="True if patient returned same day")  # ← NEW


# ==========================================
# DOCTOR DECISION MODELS
# ==========================================
class MedicineItem(BaseModel):
    name: str = Field(..., description="Medicine name")
    dosage: str = Field(..., description="e.g., 500mg")
    frequency: str = Field(..., description="e.g., Twice a day")
    duration: str = Field(..., description="e.g., 5 days")
    instructions: Optional[str] = Field(None, description="e.g., After meals")


class DoctorDecisionInput(BaseModel):
    patient_id: int
    token: str
    referral_id: Optional[str] = None
    doctor_id: str
    doctor_name: str
    decision: str = Field(..., description="Approve AI priority / Override")
    final_priority: str = Field(..., description="P1/P2/P3/P4")
    action: str = Field(..., description="Send to OPD / Send to Chemist / Refer to DH / Send to ICU")
    clinical_notes: Optional[str] = None
    medicines: Optional[List[MedicineItem]] = Field(default_factory=list)


# ==========================================
# CHEMIST DISPENSE MODELS
# ==========================================
class DispenseItem(BaseModel):
    medicine_name: str
    is_available: bool
    quantity_dispensed: Optional[int] = None
    note: Optional[str] = None


class ChemistDispenseInput(BaseModel):
    token: str
    chemist_id: str
    chemist_name: str
    dispensed_items: List[DispenseItem]
    out_of_stock_items: List[str] = Field(default_factory=list)


# ==========================================
# ICU RE-TRIAGE MODEL
# ==========================================
class ICUReTriageInput(BaseModel):
    vitals: VitalsInput
    symptoms: Optional[List[str]] = Field(default_factory=list)
    lab_findings: Optional[Dict[str, Any]] = Field(None, description="OCR lab values")