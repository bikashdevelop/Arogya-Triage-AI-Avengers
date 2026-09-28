from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
import json
import httpx

import models, schemas
from database import engine, get_db
from config import settings
from services import generate_clinical_summary
from engine.triage_engine import run_triage_assessment
from api.speech import router as speech_router
from api.ocr import router as ocr_router
from api.vision import router as vision_router


models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="AarogyaTriage Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(speech_router, prefix="/api")

app.include_router(ocr_router, prefix="/api")
app.include_router(vision_router, prefix="/api")



pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/login")


# ─────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────
def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_token(username: str, role: str) -> str:
    payload = {
        "sub": username,
        "role": role,
        "exp": datetime.utcnow() + timedelta(minutes=settings.JWT_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> models.User:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        username = payload.get("sub")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = db.query(models.User).filter(models.User.username == username).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


def require_doctor(user: models.User = Depends(get_current_user)) -> models.User:
    if user.role != "doctor":
        raise HTTPException(status_code=403, detail="Doctor access required")
    return user
def require_admin(user: models.User = Depends(get_current_user)) -> models.User:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user

# ─────────────────────────────────────────
# HEALTH
# ─────────────────────────────────────────
@app.get("/")
def health():
    return {"status": "ok", "service": "AarogyaTriage"}


# ─────────────────────────────────────────
# LOGIN
# ─────────────────────────────────────────
@app.post("/api/login", response_model=schemas.LoginResponse)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == form.username).first()
    if not user or not verify_password(form.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_token(user.username, user.role)
    return {
        "access_token": token,
        "token_type": "bearer",
        "role": user.role,
        "full_name": user.full_name,
    }


# ─────────────────────────────────────────
# TRIAGE (Nurse submits patient)
# ─────────────────────────────────────────
@app.post("/api/triage")
async def create_triage(
    req: schemas.TriageRequest,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    v = req.vitals
    text = req.symptoms_text

    # STEP 1: Rule Engine (Member 3)
    triage_input = {
        "vitals": {
            "systolic_bp": v.bp_systolic,
            "diastolic_bp": v.bp_diastolic,
            "heart_rate": v.heart_rate,
            "respiratory_rate": v.respiratory_rate,
            "temperature_f": v.temperature_f,
            "spo2": v.spo2,
        },
        "symptoms": [text],
        "facility": req.facility_type,
    }

    triage_result = run_triage_assessment(triage_input)
    mews = triage_result["mews_score"]
    tier = triage_result["triage_priority"].split()[0]

    # STEP 2: AI Summary (Groq)
    clinical = await generate_clinical_summary(text, v.dict())

    # STEP 3: Save Patient
    patient = models.Patient(
        patient_id=req.patient.patient_id,
        abha_id=req.patient.abha_id,
        age=req.patient.age,
        sex=req.patient.sex,
        name=req.patient.name,
    )
    db.add(patient)
    db.commit()
    db.refresh(patient)

    # STEP 4: Save Triage Record
    record = models.TriageRecord(
        patient_id=patient.id,
        facility_id=user.facility_id,
        symptoms_text=text,
        vitals_json=json.dumps(v.dict()),
        mews_score=mews,
        ai_priority=tier,
        assigned_department=triage_result.get("routing", {}).get("recommended_department", "General OPD"),
        ai_summary=clinical.get("summary", ""),
        ai_timeline_json=json.dumps(clinical.get("timeline", [])),
        ai_gaps_json=json.dumps(triage_result.get("identified_missing_info", [])),
        ai_questions_json=json.dumps(triage_result.get("prioritized_questions", [])),
        ai_source=clinical.get("_source", "unknown"),
        created_by=user.id,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    # STEP 5: Return Response
    return {
        "success": True,
        "data": {
            "record_id": record.id,
            "priority": tier,
            "mews_score": mews,
            "mews_breakdown": triage_result["mews_breakdown"],
            "triage_reason": triage_result["triage_reason"],
            "summary": clinical.get("summary"),
            "timeline": clinical.get("timeline", []),
            "identified_gaps": triage_result.get("identified_missing_info", []),
            "follow_up_questions": triage_result.get("prioritized_questions", []),
            "routing": triage_result.get("routing", {}),
            "ai_source": clinical.get("_source"),
            "status": "Waiting Review",
        },
    }


# ─────────────────────────────────────────
# QUEUE (Doctor dashboard)
# ─────────────────────────────────────────
@app.get("/api/queue")
def get_queue(db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    order = {"P1": 0, "P2": 1, "P3": 2, "P4": 3}
    records = db.query(models.TriageRecord).filter(
        models.TriageRecord.status == "Waiting Review"
    ).all()
    records.sort(key=lambda r: order.get(r.ai_priority, 99))

    queue = []
    for r in records:
        p = db.query(models.Patient).filter(models.Patient.id == r.patient_id).first()
        queue.append({
            "record_id": r.id,
            "patient_id": p.patient_id if p else "UNKNOWN",
            "demographics": f"{p.age}y / {p.sex}" if p else "N/A",
            "priority": r.ai_priority,
            "mews": r.mews_score,
            "symptoms": r.symptoms_text[:120],
            "status": r.status,
        })

    return {
        "success": True,
        "data": {
            "metrics": {
                "total_active": len(records),
                "p1": sum(1 for r in records if r.ai_priority == "P1"),
                "p2": sum(1 for r in records if r.ai_priority == "P2"),
            },
            "queue": queue,
        },
    }


# ─────────────────────────────────────────
# GET ONE RECORD
# ─────────────────────────────────────────
@app.get("/api/triage/{record_id}")
def get_triage(record_id: int, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    r = db.query(models.TriageRecord).filter(models.TriageRecord.id == record_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Not found")

    return {
        "success": True,
        "data": {
            "record_id": r.id,
            "symptoms_text": r.symptoms_text,
            "vitals": json.loads(r.vitals_json) if r.vitals_json else {},
            "mews_score": r.mews_score,
            "ai_priority": r.ai_priority,
            "final_priority": r.final_priority,
            "summary": r.ai_summary,
            "timeline": json.loads(r.ai_timeline_json),
            "identified_gaps": json.loads(r.ai_gaps_json),
            "follow_up_questions": json.loads(r.ai_questions_json),
            "ai_source": r.ai_source,
            "status": r.status,
        },
    }


# ─────────────────────────────────────────
# DOCTOR DECISION
# ─────────────────────────────────────────
@app.post("/api/triage/{record_id}/decision")
def doctor_decision(
    record_id: int,
    req: schemas.DecisionRequest,
    db: Session = Depends(get_db),
    doctor: models.User = Depends(require_doctor),
):
    r = db.query(models.TriageRecord).filter(models.TriageRecord.id == record_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Not found")

    r.final_priority = req.final_priority
    r.doctor_decision = req.decision
    r.clinical_notes = req.clinical_notes
    r.status = "Reviewed"
    r.reviewed_by = doctor.id
    r.reviewed_at = datetime.utcnow()
    db.commit()

    return {
        "success": True,
        "data": {
            "record_id": r.id,
            "final_priority": r.final_priority,
            "status": r.status,
        },
    }

# ─────────────────────────────────────────
# PATIENT QUEUE VIEW (public, no auth)
# ─────────────────────────────────────────
@app.get("/api/queue/me/{patient_id}")
def patient_queue_position(patient_id: str, db: Session = Depends(get_db)):
    """
    Public endpoint — patient checks their position in the queue.
    Only shows position + wait time. No medical data.
    """
    order = {"P1": 0, "P2": 1, "P3": 2, "P4": 3}
    wait_per_tier = {"P1": 5, "P2": 30, "P3": 60, "P4": 120}

    records = db.query(models.TriageRecord).filter(
        models.TriageRecord.status == "Waiting Review"
    ).all()
    records.sort(key=lambda r: order.get(r.ai_priority, 99))

    my_position = None
    my_record = None
    for i, r in enumerate(records):
        p = db.query(models.Patient).filter(models.Patient.id == r.patient_id).first()
        if p and p.patient_id == patient_id:
            my_position = i + 1
            my_record = r
            break

    if not my_record:
        raise HTTPException(
            status_code=404,
            detail="Patient not found in active queue",
        )

    patients_ahead = records[: my_position - 1]
    estimated_wait = sum(
        wait_per_tier.get(r.ai_priority, 60) for r in patients_ahead
    )

    return {
        "success": True,
        "data": {
            "patient_id": patient_id,
            "position_in_queue": my_position,
            "total_in_queue": len(records),
            "patients_ahead": my_position - 1,
            "estimated_wait_minutes": estimated_wait,
            "status": my_record.status,
        },
    }


@app.post("/api/admin/create-user")
def admin_create_user(
    username: str,
    password: str,
    role: str,
    full_name: str,
    facility_id: str,
    department: str = None,
    db: Session = Depends(get_db),
    admin: models.User = Depends(require_admin),  # NEW dependency
):
    # Check if username exists
    if db.query(models.User).filter(models.User.username == username).first():
        raise HTTPException(status_code=400, detail="Username already exists")
    
    new_user = models.User(
        username=username,
        password_hash=pwd_context.hash(password),
        role=role,
        full_name=full_name,
        facility_id=facility_id,
        department=department,
    )
    db.add(new_user)
    db.commit()
    return {"success": True, "message": f"User {username} created"}