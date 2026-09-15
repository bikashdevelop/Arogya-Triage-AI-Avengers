from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

# --- INPUT MODELS ---
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
    facility: str = Field("Primary Health Centre (PHC)", description="Current facility type")

# --- OUTPUT MODELS ---
class RoutingOutput(BaseModel):
    recommended_department: str
    referral_advice: Optional[str] = None
    immediate_checklist: List[str]

class TriageResponse(BaseModel):
    status: str
    mews_score: int
    mews_breakdown: List[str]
    triage_priority: str
    triage_reason: str
    routing: RoutingOutput
    identified_missing_info: List[str]
    prioritized_questions: List[str]
    disclaimer: str
