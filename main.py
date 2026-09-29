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

@app.get("/")
def health_check():
    return {"status": "healthy", "message": "Triage Engine is running"}

@app.post("/api/triage", response_model=TriageResponse)
async def triage_patient(data: PatientDataInput):
    import traceback
    print("\n>>> REQUEST RECEIVED <<<")
    print("Data:", data.model_dump())
    try:
        result = run_triage_assessment(data.model_dump())
        print(">>> SUCCESS <<<")
        return result
    except Exception as e:
        print("\n" + "="*50)
        print("===== ERROR OCCURRED =====")
        print("Error Type:", type(e).__name__)
        print("Error Message:", str(e))
        traceback.print_exc()
        print("="*50 + "\n")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

if __name__ == "__main__":
    print("\n Starting AarogyaTriage Backend...")
    print(" API Endpoint: http://localhost:8000/api/triage")
    print(" Interactive Docs: http://localhost:8000/docs\n")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)