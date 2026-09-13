from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
import json

import models, schemas
from database import engine, get_db
from config import settings
from services import generate_clinical_summary

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="AarogyaTriage Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/login")


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


@app.get("/")
def health():
    return {"status": "ok", "service": "AarogyaTriage"}


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


@app.post("/api/triage")
async def create_triage(
    req: schemas.TriageRequest,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    v = req.vitals
    text = req.symptoms_text

    try:
        from engine.mews_calculator import calculate_mews
        from engine.triage_logic import assign_priority
        mews = calculate_mews(v.bp_systolic, v.heart_rate, v.respiratory_rate, v.temperature_f, v.spo2)
        priority = assign_priority(mews, text)
        tier = priority["tier"]
    except ImportError:
        mews = 0
        tier = "P3"

    clinical = await generate_clinical_summary(text, v.dict())

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

    record = models.TriageRecord(
        patient_id=patient.id,
        symptoms_text=text,
        vitals_json=json.dumps(v.dict()),
        mews_score=mews,
        ai_priority=tier,
        ai_summary=clinical.get("summary", ""),
        ai_timeline_json=json.dumps(clinical.get("timeline", [])),
        ai_gaps_json=json.dumps(clinical.get("identified_gaps", [])),
        ai_questions_json=json.dumps(clinical.get("follow_up_questions", [])),
        ai_source=clinical.get("_source", "unknown"),
        created_by=user.id,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    return {
        "success": True,
        "data": {
            "record_id": record.id,
            "priority": tier,
            "mews_score": mews,
            "summary": clinical.get("summary"),
            "timeline": clinical.get("timeline", []),
            "identified_gaps": clinical.get("identified_gaps", []),
            "follow_up_questions": clinical.get("follow_up_questions", []),
            "ai_source": clinical.get("_source"),
        },
    }


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