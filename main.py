from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from models import PatientDataInput, TriageResponse
from triage_engine import run_triage_assessment

app = FastAPI(
    title="AarogyaTriage API - Member 3 Backend",
    description="Clinical Rule Engine for MEWS, Triage Prioritization, and Routing",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/api/triage", response_model=TriageResponse)
async def triage_patient(data: PatientDataInput):
    import traceback
    try:
        result = run_triage_assessment(data.model_dump())
        return result
    except Exception as e:
        print("===== ERROR OCCURRED =====")
        traceback.print_exc()
        print("==========================")
        raise HTTPException(status_code=500, detail=f"Triage Engine Error: {str(e)}")
