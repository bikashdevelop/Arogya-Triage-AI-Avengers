from pydantic import BaseModel, Field
from typing import List


class LoginRequest(BaseModel):
    username: str
    password: str


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
    abha_id: str
    age: int
    sex: str
    name: str


class TriageRequest(BaseModel):
    patient: PatientInput
    symptoms_text: str
    vitals: Vitals
    facility_type: str = "PHC"


class DecisionRequest(BaseModel):
    decision: str = Field(..., pattern="^(approve|override)$")
    final_priority: str = Field(..., pattern="^(P1|P2|P3|P4)$")
    clinical_notes: str = ""
    action: str = Field("opd", pattern="^(admit|refer|opd)$")