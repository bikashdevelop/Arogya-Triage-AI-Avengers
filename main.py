from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from datetime import datetime
from typing import List, Dict, Any

from models import (
    PatientDataInput,
    TriageResponse,
    DoctorDecisionInput,
    ChemistDispenseInput
)
from triage_engine import run_triage_assessment


app = FastAPI(
    title="AarogyaTriage API - Complete Workflow",
    description="Nurse + Doctor + Chemist Workflow with Age-Aware Rule Engine",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==========================================
# IN-MEMORY STORAGE
# ==========================================
triage_queue: List[Dict[str, Any]] = []
opd_queue: List[Dict[str, Any]] = []
icu_queue: List[Dict[str, Any]] = []
doctor_decisions: List[Dict[str, Any]] = []
prescriptions_store: Dict[str, Dict[str, Any]] = {}
dispensed_records: List[Dict[str, Any]] = []

# Counters
patient_counter = 0
token_counter = 1000
prescription_counter = 0


def generate_token() -> str:
    """T-1001, T-1002, ..."""
    global token_counter
    token_counter += 1
    return f"T-{token_counter}"


def find_patient_by_abha(abha_id: str) -> Dict[str, Any]:
    """ABHA ID se patient dhundho - queue mein"""
    if not abha_id or abha_id == "N/A":
        return None
    for p in triage_queue:
        if p["patient_info"].get("abha_id") == abha_id:
            return p
    return None


# ==========================================
# 1. HEALTH CHECK
# ==========================================
@app.get("/")
def health_check():
    return {"status": "healthy", "message": "AarogyaTriage Engine is running"}


# ==========================================
# 2. NURSE PAGE - TRIAGE + TOKEN
# ==========================================
@app.post("/api/triage", response_model=TriageResponse)
async def triage_patient(data: PatientDataInput):
    global patient_counter
    import traceback
    print("\n>>> REQUEST RECEIVED <<<")
    try:
        # Step 1: Triage engine chalao
        result = run_triage_assessment(data.model_dump())

        # Step 2: Check karo - kya patient pehle se queue mein hai? (ABHA ID se)
        abha_id = data.demographics.get("abha_id", "N/A")
        existing_patient = find_patient_by_abha(abha_id)

        if existing_patient:
            # Wahi token use karo (same day re-visit)
            token = existing_patient["token"]
            patient_id = existing_patient["id"]
            print(f">>> EXISTING PATIENT: Token {token} reused <<<")
        else:
            # Naya token generate karo
            patient_counter += 1
            patient_id = patient_counter
            token = generate_token()
            print(f">>> NEW PATIENT: Token {token} assigned <<<")

        # Step 3: Queue record
        queue_record = {
            "id": patient_id,
            "token": token,
            "timestamp": datetime.now().isoformat(),
            "patient_info": {
                "name": data.demographics.get("name", "Anonymous"),
                "age": data.demographics.get("age"),
                "gender": data.demographics.get("gender"),
                "abha_id": abha_id
            },
            "vitals": data.vitals.model_dump(),
            "symptoms": data.symptoms,
            "lab_findings": data.lab_findings,
            "facility": data.facility,
            "triage_result": result,
            "age_group": result.get("age_group"),
            "patient_type": result.get("patient_type")
        }

        # Agar existing patient hai toh update karo, warna naya add karo
        if existing_patient:
            idx = triage_queue.index(existing_patient)
            triage_queue[idx] = queue_record
        else:
            triage_queue.append(queue_record)

        # Step 4: Response mein token + queue_id
        result["queue_id"] = patient_id
        result["token_number"] = token
        result["is_existing_patient"] = existing_patient is not None
        return result

    except Exception as e:
        print("\n" + "="*50)
        print("===== TRIAGE ERROR =====")
        traceback.print_exc()
        print("="*50 + "\n")
        raise HTTPException(status_code=500, detail=f"Triage Error: {str(e)}")


# ==========================================
# 3. DOCTOR QUEUE
# ==========================================
@app.get("/api/queue")
def get_doctor_queue():
    priority_order = {"P1": 1, "P2": 2, "P3": 3, "P4": 4}
    sorted_queue = sorted(
        triage_queue,
        key=lambda x: (
            priority_order.get(x["triage_result"]["triage_priority"].split()[0], 5),
            -x["triage_result"]["mews_score"],
            x["timestamp"]
        )
    )
    return {"total_patients": len(sorted_queue), "queue": sorted_queue}


# ==========================================
# 4. DOCTOR DECISION + PRESCRIPTION
# ==========================================
@app.post("/api/doctor/decision")
def save_doctor_decision(data: DoctorDecisionInput):
    global prescription_counter

    doctor_decisions.append({
        "patient_id": data.patient_id,
        "token": data.token,
        "doctor_id": data.doctor_id,
        "doctor_name": data.doctor_name,
        "decision": data.decision,
        "final_priority": data.final_priority,
        "action": data.action,
        "clinical_notes": data.clinical_notes,
        "timestamp": datetime.now().isoformat()
    })

    response = {
        "status": "success",
        "action_taken": data.action,
        "token": data.token,
        "prescription_ready": False
    }

    # Action 1: Send to OPD
    if data.action == "Send to OPD":
        opd_queue.append({
            "patient_id": data.patient_id,
            "token": data.token,
            "priority": data.final_priority,
            "added_at": datetime.now().isoformat()
        })
        response["message"] = f"Patient {data.token} sent to OPD"

    # Action 2: Send to Chemist
    elif data.action == "Send to Chemist":
        if data.medicines and len(data.medicines) > 0:
            prescription_counter += 1

            patient_record = next((p for p in triage_queue if p["id"] == data.patient_id), None)
            patient_name = patient_record["patient_info"]["name"] if patient_record else "N/A"
            patient_age = patient_record["patient_info"]["age"] if patient_record else "N/A"
            patient_gender = patient_record["patient_info"]["gender"] if patient_record else "N/A"
            patient_abha = patient_record["patient_info"]["abha_id"] if patient_record else "N/A"

            prescription_record = {
                "prescription_id": prescription_counter,
                "token": data.token,
                "patient_id": data.patient_id,
                "patient_name": patient_name,
                "age_gender": f"{patient_age} / {patient_gender}",
                "abha_id": patient_abha,
                "doctor_id": data.doctor_id,
                "doctor_name": data.doctor_name,
                "medicines": [m.model_dump() for m in data.medicines],
                "clinical_notes": data.clinical_notes,
                "created_at": datetime.now().isoformat(),
                "status": "pending",
                "chemist_id": None,
                "chemist_name": None,
                "dispensed_at": None,
                "dispensed_items": [],
                "out_of_stock_items": []
            }
            prescriptions_store[data.token] = prescription_record

            response["prescription_ready"] = True
            response["prescription_id"] = prescription_counter
            response["message"] = f"Prescription #{prescription_counter} created for Token {data.token}"

    # Action 3: Refer to DH
    elif data.action == "Refer to DH":
        referral_id = f"REF-{datetime.now().strftime('%Y%m%d')}-{data.patient_id:04d}"
        response["message"] = f"Patient {data.token} referred to DH"
        response["referral_id"] = referral_id

    # Action 4: Send to ICU
    elif data.action == "Send to ICU":
        icu_queue.append({
            "patient_id": data.patient_id,
            "token": data.token,
            "priority": data.final_priority,
            "notes": data.clinical_notes,
            "added_at": datetime.now().isoformat(),
            "vitals_history": []    # ICU monitoring ke liye
        })
        response["message"] = f"Patient {data.token} admitted to ICU"

    else:
        raise HTTPException(status_code=400, detail=f"Invalid action: {data.action}")

    return response


# ==========================================
# 5. REMOVE FROM QUEUE
# ==========================================
@app.post("/api/queue/{patient_id}/review")
def mark_as_reviewed(patient_id: int):
    global triage_queue
    triage_queue = [p for p in triage_queue if p["id"] != patient_id]
    return {"status": "success", "message": f"Patient {patient_id} removed from queue"}


# ==========================================
# 5.5 ICU RE-TRIAGE (Continuous Monitoring)
# ==========================================
@app.post("/api/icu/re-triage/{token}")
async def icu_re_triage(token: str, data: dict):
    """
    ICU mein patient ke naye vitals aaye toh re-triage karo.
    """
    token = token.strip().upper()
    
    # ICU queue mein dhundho
    icu_patient = next((p for p in icu_queue if p["token"] == token), None)
    
    if not icu_patient:
        raise HTTPException(status_code=404, detail=f"Token {token} not in ICU queue")
    
    # Naye vitals aur symptoms
    new_vitals = data.get("vitals", {})
    new_symptoms = data.get("symptoms", [])
    lab_findings = data.get("lab_findings", {})
    
    # Re-triage chalao
    triage_data = {
        "demographics": {"age": 30, "gender": "Unknown"},  # ICU mein already known
        "vitals": new_vitals,
        "symptoms": new_symptoms,
        "lab_findings": lab_findings,
        "patient_category": "None",
        "facility": "ICU"
    }
    
    new_result = run_triage_assessment(triage_data)
    
    # History mein add karo
    icu_patient["vitals_history"].append({
        "timestamp": datetime.now().isoformat(),
        "mews_score": new_result["mews_score"],
        "triage_priority": new_result["triage_priority"],
        "vitals": new_vitals
    })
    
    # Trend check karo (improving ya deteriorating)
    history = icu_patient["vitals_history"]
    trend = "stable"
    if len(history) >= 2:
        old_mews = history[-2]["mews_score"]
        new_mews = history[-1]["mews_score"]
        if new_mews > old_mews:
            trend = "deteriorating"
        elif new_mews < old_mews:
            trend = "improving"
    
    # Discharge readiness check
    discharge_ready = False
    if len(history) >= 3:
        last_3 = [h["mews_score"] for h in history[-3:]]
        if all(m <= 1 for m in last_3):
            discharge_ready = True
    
    return {
        "status": "success",
        "token": token,
        "new_mews": new_result["mews_score"],
        "new_priority": new_result["triage_priority"],
        "trend": trend,
        "discharge_ready": discharge_ready,
        "recommendation": (
            "✅ Discharge ready — shift to ward" if discharge_ready
            else "🚨 Deteriorating — alert doctor" if trend == "deteriorating"
            else "✅ Improving — continue monitoring" if trend == "improving"
            else "🔄 Stable — continue monitoring"
        )
    }


# ==========================================
# 5.6 ICU QUEUE
# ==========================================
@app.get("/api/icu/queue")
def get_icu_queue():
    return {
        "total_patients": len(icu_queue),
        "queue": icu_queue
    }


# ==========================================
# 6. CHEMIST - TOKEN SE PRESCRIPTION DHUNDHO
# ==========================================
@app.get("/api/chemist/prescription/{token}")
def get_prescription_by_token(token: str):
    token = token.strip().upper()
    prescription = prescriptions_store.get(token)

    if not prescription:
        raise HTTPException(
            status_code=404,
            detail=f"No prescription found for Token: {token}"
        )

    if prescription["status"] == "dispensed":
        return {
            "status": "already_dispensed",
            "message": f"Token {token} already dispensed on {prescription.get('dispensed_at')}",
            "prescription": prescription
        }

    return {
        "status": "success",
        "token": token,
        "prescription": prescription
    }


# ==========================================
# 7. CHEMIST - DISPENSE MEDICINE
# ==========================================
@app.post("/api/chemist/dispense")
def dispense_medicine(data: ChemistDispenseInput):
    token = data.token.strip().upper()
    prescription = prescriptions_store.get(token)

    if not prescription:
        raise HTTPException(status_code=404, detail=f"Token {token} not found")

    if prescription["status"] == "dispensed":
        raise HTTPException(status_code=400, detail=f"Token {token} already dispensed")

    prescription["status"] = "dispensed"
    prescription["chemist_id"] = data.chemist_id
    prescription["chemist_name"] = data.chemist_name
    prescription["dispensed_at"] = datetime.now().isoformat()
    prescription["dispensed_items"] = [d.model_dump() for d in data.dispensed_items]
    prescription["out_of_stock_items"] = data.out_of_stock_items

    dispensed_records.append({
        "token": token,
        "prescription_id": prescription.get("prescription_id"),
        "chemist_id": data.chemist_id,
        "chemist_name": data.chemist_name,
        "dispensed_at": prescription["dispensed_at"],
        "medicines_count": len(data.dispensed_items),
        "out_of_stock_count": len(data.out_of_stock_items)
    })

    return {
        "status": "success",
        "message": f"Prescription for Token {token} dispensed successfully",
        "token": token,
        "chemist_name": data.chemist_name,
        "dispensed_at": prescription["dispensed_at"],
        "print_ready": True
    }


# ==========================================
# 8. PRINT PRESCRIPTION
# ==========================================
@app.get("/api/chemist/print/{token}")
def print_prescription(token: str):
    token = token.strip().upper()
    prescription = prescriptions_store.get(token)

    if not prescription:
        raise HTTPException(status_code=404, detail=f"Token {token} not found")

    if prescription["status"] != "dispensed":
        raise HTTPException(status_code=400, detail="Prescription not yet dispensed")

    return {
        "header": {
            "facility": "AarogyaTriage - Primary Health Centre (PHC)",
            "date": datetime.now().strftime("%d-%b-%Y"),
            "token": token,
            "prescription_id": prescription.get("prescription_id")
        },
        "patient": {
            "patient_id": prescription.get("patient_id"),
            "name": prescription.get("patient_name", "N/A"),
            "age_gender": prescription.get("age_gender", "N/A"),
            "abha_id": prescription.get("abha_id", "N/A")
        },
        "doctor": {
            "name": prescription.get("doctor_name", "N/A"),
            "id": prescription.get("doctor_id", "N/A")
        },
        "diagnosis": prescription.get("clinical_notes", "N/A"),
        "medicines": prescription.get("dispensed_items", []),
        "out_of_stock": prescription.get("out_of_stock_items", []),
        "chemist": {
            "name": prescription.get("chemist_name", "N/A"),
            "id": prescription.get("chemist_id", "N/A"),
            "dispensed_at": prescription.get("dispensed_at")
        },
        "disclaimer": "This is a digitally dispensed prescription. Non-diagnostic advisory only."
    }


# ==========================================
# 9. CHEMIST STATS
# ==========================================
@app.get("/api/chemist/stats")
def get_chemist_stats():
    today = datetime.now().strftime("%Y-%m-%d")
    today_dispensed = [d for d in dispensed_records if d["dispensed_at"].startswith(today)]
    pending_count = len([p for p in prescriptions_store.values() if p["status"] == "pending"])

    return {
        "pending_prescriptions": pending_count,
        "dispensed_today": len(today_dispensed),
        "total_prescriptions": len(prescriptions_store)
    }


# ==========================================
# SERVER START
# ==========================================
if __name__ == "__main__":
    print("\n Starting AarogyaTriage Backend...")
    print(" Nurse API:   http://localhost:8000/api/triage")
    print(" Doctor API:  http://localhost:8000/api/queue")
    print(" ICU API:     http://localhost:8000/api/icu/queue")
    print(" Chemist API: http://localhost:8000/api/chemist/prescription/{token}")
    print(" Interactive Docs: http://localhost:8000/docs\n")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
