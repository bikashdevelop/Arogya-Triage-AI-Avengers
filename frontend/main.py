"""
AarogyaTriage — Full Hospital Workflow Backend.
"""
from __future__ import annotations

import asyncio, csv, json, logging, os, time, uuid
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Any, Deque, Dict, List, Optional, Tuple

from fastapi import (
    Depends, FastAPI, File, Form, HTTPException, Request, UploadFile, status,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

import models, schemas
from config import settings
from database import engine, get_db, SessionLocal

# ─── Groq SDK (optional) ───
try:
    from groq import Groq
    _GROQ_AVAILABLE = True
except ImportError:
    Groq = None
    _GROQ_AVAILABLE = False

# ─── Doctor assignment engine ───
try:
    from app.engine.doctor_assigner import assign_doctor, estimate_wait
except ImportError:
    def assign_doctor(*a, **k):
        return {"chosen_doctor": None, "score": 0,
                "reasons": ["Assigner unavailable"], "candidate_scores": [],
                "fallback_used": None, "total_considered": 0}
    def estimate_wait(*a, **k):
        return 0

# ─── Clinical summary (Groq) + Speech transcription (Sarvam) ───
try:
    from app.services.llm_orchestrator import (
        generate_clinical_summary,
        transcribe_audio,
    )
    _TRANSCRIBE_AVAILABLE = True
except ImportError as _imp_err:
    _TRANSCRIBE_AVAILABLE = False
    _transcribe_import_error = str(_imp_err)
    async def generate_clinical_summary(*a, **k):
        return {"summary": "AI unavailable", "timeline": [],
                "missing_information": [], "translated_symptoms": "",
                "_source": "stub"}
    def transcribe_audio(*a, **k):
        return {"text": "", "original": "", "language": "en",
                "translated": False, "_source": "stub",
                "_error": "llm_orchestrator not available"}
else:
    _transcribe_import_error = None

# ─── Triage engine ───
try:
    from app.engine.triage_engine import run_triage_assessment
except ImportError:
    def run_triage_assessment(*a, **k):
        return {
            "provisional_triage": {"priority_code": "P3", "label": "STANDARD", "color": "GREEN"},
            "physiological_deterioration": {"mews_score": 0, "mews_breakdown": [], "escalation": {}},
            "routing": {"recommended_department": "General OPD"},
            "identified_missing_info": [], "prioritized_questions": [],
            "triage_reasoning": ["Fallback"],
        }

# ─── Referral navigator ───
try:
    from app.engine.referral_navigator import recommend_referral
except ImportError:
    def recommend_referral(**k):
        class _R:
            priority = "P3"; priority_label = "ROUTINE"
            urgency_reasons = []; service_reasons = []; facility_reasons = []
            suggested_service_code = "GEN_MED"; suggested_service_name = "General Medicine"
            suggested_facility_id = None; suggested_facility_name = None
            suggested_facility_type = None
            availability_confidence = "UNVERIFIED"; last_verified_at = None
            fallback_facilities = []; emergency_pathway = False
            routing_confidence = "LOW"
            def to_dict(self):
                return {"priority": self.priority,
                        "suggested_service_name": self.suggested_service_name}
        return _R()

# ─── Optional routers ───
_extra_routers_import_error: Optional[Exception] = None
try:
    from app.api.speech import router as speech_router
    from app.api.ocr import router as ocr_router
    from app.api.vision import router as vision_router
    _EXTRA_ROUTERS_AVAILABLE = True
except ImportError as exc:
    _EXTRA_ROUTERS_AVAILABLE = False
    _extra_routers_import_error = exc

# ─── Logging ───
logging.basicConfig(
    level=getattr(logging, getattr(settings, "LOG_LEVEL", "INFO").upper(), logging.INFO),
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger("aarogyatriage")

# ─── Groq client ───
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
groq_client = Groq(api_key=GROQ_API_KEY) if (_GROQ_AVAILABLE and GROQ_API_KEY) else None

# Current Groq model
GROQ_MODEL = "openai/gpt-oss-120b"

if groq_client:
    logger.info("✓ Groq client initialized. Model: %s", GROQ_MODEL)
else:
    logger.warning("✗ Groq client NOT initialized — check GROQ_API_KEY in .env")

# ─── Sarvam diagnostic at startup ───
_SARVAM_API_KEY = os.getenv("SARVAM_API_KEY")
if _SARVAM_API_KEY:
    logger.info("✓ SARVAM_API_KEY is set (…%s)", _SARVAM_API_KEY[-4:])
else:
    logger.warning("✗ SARVAM_API_KEY NOT set — /api/transcribe will fail")
if _TRANSCRIBE_AVAILABLE:
    logger.info("✓ transcribe_audio imported from llm_orchestrator")
else:
    logger.error("✗ transcribe_audio import failed: %s", _transcribe_import_error)

# ═══════════════════════════════════════════════════════════
# BACKGROUND AI WORKER
# ═══════════════════════════════════════════════════════════
async def process_pending_ai_records():
    db = SessionLocal()
    try:
        pending = db.query(models.TriageRecord).filter(
            models.TriageRecord.status == "PENDING_AI").limit(5).all()
        for record in pending:
            try:
                vitals_dict = json.loads(record.vitals_json) if record.vitals_json else {}
                patient = db.query(models.Patient).filter(
                    models.Patient.id == record.patient_id).first()
                clinical = await generate_clinical_summary(
                    symptoms_text=record.symptoms_text, vitals=vitals_dict,
                    duration=patient.duration_of_symptoms if patient else None,
                    severity=patient.severity if patient else None,
                    medical_history=patient.medical_history if patient else None,
                    allergies=patient.allergies if patient else None,
                    medications=patient.current_medications if patient else None)
                record.ai_summary = clinical.get("summary", "")
                record.ai_timeline_json = json.dumps(clinical.get("timeline", []))
                record.ai_gaps_json = json.dumps(clinical.get("missing_information", []))
                record.ai_explanation = clinical.get("explanation", "")
                record.status = "Waiting Review"
                db.commit()
            except Exception as e:
                logger.error(f"AI processing failed for {record.id}: {e}")
                db.rollback()
    except Exception as e:
        logger.error(f"Background worker error: {e}")
    finally:
        db.close()

async def run_periodic_ai_check():
    while True:
        await process_pending_ai_records()
        await asyncio.sleep(30)

# ═══════════════════════════════════════════════════════════
# LIFESPAN
# ═══════════════════════════════════════════════════════════
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("AarogyaTriage starting up…")
    if getattr(settings, "AUTO_CREATE_TABLES", True):
        try:
            models.Base.metadata.create_all(bind=engine)
            logger.info("Database tables ensured.")
        except SQLAlchemyError as exc:
            logger.exception("Failed to create tables: %s", exc)
            raise
    task = asyncio.create_task(run_periodic_ai_check())
    yield
    task.cancel()

app = FastAPI(
    title="AarogyaTriage Backend", version="3.0.0",
    lifespan=lifespan, docs_url="/docs", redoc_url="/redoc")

# ═══════════════════════════════════════════════════════════
# CONFIG / MIDDLEWARE
# ═══════════════════════════════════════════════════════════
def _parse_origins(raw):
    if isinstance(raw, str):
        return [o.strip() for o in raw.split(",") if o.strip()]
    return list(raw or ["*"])

_ALLOWED_ORIGINS = _parse_origins(getattr(settings, "CORS_ORIGINS", ["*"]))
_ALLOW_CREDENTIALS = _ALLOWED_ORIGINS != ["*"]
_ENABLE_HSTS = bool(getattr(settings, "ENABLE_HSTS", False))

_SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff", "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
}
if _ENABLE_HSTS:
    _SECURITY_HEADERS["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"

def _security_headers(request):
    h = dict(_SECURITY_HEADERS)
    h["X-Request-ID"] = getattr(request.state, "request_id", "")
    return h

app.add_middleware(
    CORSMiddleware, allow_origins=_ALLOWED_ORIGINS,
    allow_credentials=_ALLOW_CREDENTIALS,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    expose_headers=["X-Request-ID"], max_age=600)
app.add_middleware(GZipMiddleware, minimum_size=1024)

@app.middleware("http")
async def request_context_middleware(request: Request, call_next):
    rid = request.headers.get("X-Request-ID") or uuid.uuid4().hex
    request.state.request_id = rid
    start = time.perf_counter()
    response = await call_next(request)
    for k, v in _SECURITY_HEADERS.items():
        response.headers.setdefault(k, v)
    response.headers.setdefault("X-Request-ID", rid)
    logger.info("rid=%s %s %s -> %s %.1fms", rid, request.method,
                request.url.path, response.status_code,
                (time.perf_counter() - start) * 1000)
    return response

# ═══════════════════════════════════════════════════════════
# EXCEPTION HANDLERS
# ═══════════════════════════════════════════════════════════
def _error_payload(request, code, message, sc):
    return {"success": False,
            "error": {"code": code, "message": message,
                      "request_id": getattr(request.state, "request_id", None)},
            "status_code": sc}

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    d = exc.detail
    msg = d if isinstance(d, (dict, list)) else str(d)
    h = _security_headers(request)
    if getattr(exc, "headers", None):
        h.update(exc.headers)
    return JSONResponse(status_code=exc.status_code,
        content=_error_payload(request, "http_error", msg, exc.status_code), headers=h)

@app.exception_handler(IntegrityError)
async def integrity_error_handler(request, exc):
    return JSONResponse(status_code=409,
        content=_error_payload(request, "conflict", "Resource conflict.", 409),
        headers=_security_headers(request))

@app.exception_handler(Exception)
async def unhandled_exception_handler(request, exc):
    logger.exception("Unhandled exception rid=%s",
                     getattr(request.state, "request_id", None))
    return JSONResponse(status_code=500,
        content=_error_payload(request, "internal_error", "Internal server error.", 500),
        headers=_security_headers(request))

# ═══════════════════════════════════════════════════════════
# AUTH PRIMITIVES
# ═══════════════════════════════════════════════════════════
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/login")

def _utcnow():
    return datetime.now(timezone.utc)

def verify_password(p, h):
    try:
        return pwd_context.verify(p, h)
    except Exception:
        return False

def hash_password(p):
    return pwd_context.hash(p)

def create_token(username, role):
    now = _utcnow()
    payload = {"sub": username, "role": role,
               "iat": int(now.timestamp()), "nbf": int(now.timestamp()),
               "jti": uuid.uuid4().hex, "type": "access",
               "exp": now + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)}
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)

def get_current_user(token: str = Depends(oauth2_scheme),
                     db: Session = Depends(get_db)) -> models.User:
    exc = HTTPException(status_code=401, detail="Invalid or expired token",
                        headers={"WWW-Authenticate": "Bearer"})
    try:
        payload = jwt.decode(token, settings.JWT_SECRET,
                             algorithms=[settings.JWT_ALGORITHM])
    except JWTError:
        raise exc
    if payload.get("type") != "access":
        raise exc
    u = payload.get("sub")
    if not u:
        raise exc
    user = db.query(models.User).filter(models.User.username == u).first()
    if not user:
        raise exc
    return user

def require_doctor(user: models.User = Depends(get_current_user)):
    if user.role != "doctor":
        raise HTTPException(403, "Doctor access required")
    return user

def require_admin(user: models.User = Depends(get_current_user)):
    if user.role != "admin":
        raise HTTPException(403, "Admin access required")
    return user

# ═══════════════════════════════════════════════════════════
# LOGIN RATE LIMITING
# ═══════════════════════════════════════════════════════════
_LOGIN_WINDOW_SECONDS = 60
_LOGIN_MAX_ATTEMPTS = 8
_PRUNE_EVERY_N_CALLS = 256
_login_attempts: Dict[str, Deque[float]] = defaultdict(deque)
_login_check_counter = 0

def _prune_login_buckets():
    now = time.time()
    for key in list(_login_attempts.keys()):
        b = _login_attempts[key]
        while b and now - b[0] > _LOGIN_WINDOW_SECONDS:
            b.popleft()
        if not b:
            _login_attempts.pop(key, None)

def _check_login_rate_limit(key):
    global _login_check_counter
    _login_check_counter += 1
    if _login_check_counter % _PRUNE_EVERY_N_CALLS == 0:
        _prune_login_buckets()
    now = time.time()
    b = _login_attempts[key]
    while b and now - b[0] > _LOGIN_WINDOW_SECONDS:
        b.popleft()
    if len(b) >= _LOGIN_MAX_ATTEMPTS:
        raise HTTPException(429, "Too many login attempts.")

def _record_failed_login(key):
    _login_attempts[key].append(time.time())

def _clear_login_attempts(key):
    _login_attempts.pop(key, None)

# ═══════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════
def _to_dict(obj):
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    return obj.dict()

def _safe_json_loads(raw, default):
    if not raw:
        return default
    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        return default

def generate_patient_id(db):
    today = _utcnow().strftime("%Y%m%d")
    prefix = f"PAT-{today}-"
    c = db.query(models.Patient).filter(
        models.Patient.patient_id.like(f"{prefix}%")).count()
    return f"{prefix}{c + 1:03d}"

def _run_triage(vitals, text, facility_type, category="None", age=30,
                gender="Unknown", lab_findings=None, duration=None, symptom_onset=None):
    ti = {
        "demographics": {"age": age, "gender": gender},
        "vitals": {
            "systolic_bp": vitals.bp_systolic, "diastolic_bp": vitals.bp_diastolic,
            "heart_rate": vitals.heart_rate, "respiratory_rate": vitals.respiratory_rate,
            "temperature_f": vitals.temperature_f, "spo2": vitals.spo2,
        },
        "symptoms": [text],
        "duration": duration,
        "symptom_onset": symptom_onset,
        "lab_findings": lab_findings or {},
        "patient_category": ("Pregnancy" if category == "Pregnancy"
                             else "Child" if category == "Child" else "Adult"),
        "facility": facility_type,
    }
    try:
        result = run_triage_assessment(ti)
        tier = result.get("provisional_triage", {}).get("priority_code", "P3")
        mews = result.get("physiological_deterioration", {}).get("mews_score", 0)
        return result, mews, tier
    except Exception:
        logger.exception("Triage engine failed")
        return {
            "provisional_triage": {"priority_code": "P3", "label": "STANDARD", "color": "GREEN"},
            "physiological_deterioration": {"mews_score": 0, "mews_breakdown": [], "escalation": {}},
            "routing": {"recommended_department": "General OPD"},
            "identified_missing_info": [], "prioritized_questions": [],
            "triage_reasoning": ["Fallback"],
        }, 0, "P3"

def _fetch_patients_map(db, pks):
    if not pks:
        return {}
    return {p.id: p for p in db.query(models.Patient).filter(
        models.Patient.id.in_(set(pks))).all()}

# ═══════════════════════════════════════════════════════════
# HEALTH
# ═══════════════════════════════════════════════════════════
@app.get("/", tags=["health"])
def health():
    return {"status": "ok", "service": "AarogyaTriage", "version": app.version}

@app.get("/healthz", tags=["health"])
def healthz():
    return {"status": "ok"}

@app.get("/readyz", tags=["health"])
def readyz(db: Session = Depends(get_db)):
    try:
        db.execute(models.User.__table__.select().limit(1))
    except Exception:
        raise HTTPException(503, "Database not ready")
    return {"status": "ready"}

# ═══════════════════════════════════════════════════════════
# AUTH
# ═══════════════════════════════════════════════════════════
@app.post("/api/login", response_model=schemas.LoginResponse, tags=["auth"])
def login(request: Request, form: OAuth2PasswordRequestForm = Depends(),
          db: Session = Depends(get_db)):
    key = f"{request.client.host if request.client else 'x'}:{form.username}"
    _check_login_rate_limit(key)
    user = db.query(models.User).filter(
        models.User.username == form.username).first()
    if not user or not verify_password(form.password, user.password_hash):
        _record_failed_login(key)
        raise HTTPException(401, "Invalid credentials")
    _clear_login_attempts(key)
    return {"access_token": create_token(user.username, user.role),
            "token_type": "bearer", "role": user.role, "full_name": user.full_name}

# ═══════════════════════════════════════════════════════════
# REGISTRATION
# ═══════════════════════════════════════════════════════════
@app.post("/api/register", tags=["registration"])
def register_patient(
    name: str = Form(...), age: int = Form(None), sex: str = Form("Unknown"),
    mobile: str = Form(None), email: str = Form(None),
    category: str = Form("None"),
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    if user.role not in ("reception", "admin", "nurse"):
        raise HTTPException(403, "Only reception/admin can register")
    today = _utcnow().strftime("%Y%m%d")
    prefix = f"OPD-{today}-"
    c = db.query(models.Patient).filter(
        models.Patient.patient_id.like(f"{prefix}%")).count()
    token_id = f"{prefix}{c + 1:03d}"
    try:
        p = models.Patient(patient_id=token_id, name=name, age=age, sex=sex,
                           mobile=mobile, email=email, category=category,
                           consent_given=False)
        db.add(p)
        db.add(models.AuditLog(user_id=user.id, record_id=None,
                               action="PATIENT_REGISTERED",
                               details=f"Token {token_id} by {user.full_name}"))
        db.commit()
        db.refresh(p)
    except Exception as e:
        db.rollback()
        raise HTTPException(500, str(e))
    return {"success": True, "data": {"patient_id": token_id, "name": name,
            "age": age, "sex": sex, "next_step": "Send to Triage (Nurse)"}}

# ═══════════════════════════════════════════════════════════
# EMERGENCY BYPASS
# ═══════════════════════════════════════════════════════════
@app.post("/api/triage/emergency", tags=["triage"])
async def emergency_bypass(
    chief_complaint: str = Form(...), age: int = Form(None),
    sex: str = Form("Unknown"), name: str = Form("Unknown Emergency"),
    bp_systolic: int = Form(None), bp_diastolic: int = Form(None),
    heart_rate: int = Form(None), spo2: int = Form(None),
    reason: str = Form(...),
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    if user.role not in ("nurse", "doctor", "admin"):
        raise HTTPException(403, "Only clinical staff can trigger bypass")
    pid = generate_patient_id(db)
    try:
        p = models.Patient(patient_id=pid, name=name, age=age, sex=sex,
                           category="None", consent_given=True,
                           medical_history="EMERGENCY_BYPASS")
        db.add(p)
        db.flush()
        vitals = {"bp_systolic": bp_systolic or 0, "bp_diastolic": bp_diastolic or 0,
                  "heart_rate": heart_rate or 0, "spo2": spo2 or 0,
                  "temperature_f": 0, "respiratory_rate": 0}
        r = models.TriageRecord(
            patient_id=p.id, facility_id=getattr(user, "facility_id", None),
            symptoms_text=chief_complaint, vitals_json=json.dumps(vitals),
            mews_score=6, ai_priority="P1", priority_window_mins=0,
            assigned_department="Emergency / Trauma",
            ai_summary=f"[EMERGENCY BYPASS] {chief_complaint}",
            ai_timeline_json=json.dumps(["Patient arrived", "Emergency bypass activated"]),
            ai_gaps_json=json.dumps(["Vitals incomplete", "History not collected"]),
            ai_explanation=f"EMERGENCY BYPASS by {user.full_name}. Reason: {reason}",
            follow_up_answers_json="{}", ai_source="emergency_bypass",
            status="Waiting Review", created_by=user.id, is_manually_assigned=True,
        )
        db.add(r)
        db.add(models.AuditLog(user_id=user.id, record_id=r.id,
                               action="EMERGENCY_BYPASS",
                               details=f"Bypass by {user.full_name}. Reason: {reason}"))
        db.commit()
        db.refresh(r)
    except Exception as e:
        db.rollback()
        raise HTTPException(500, str(e))
    return {"success": True, "data": {
        "record_id": r.id, "patient_id": pid, "priority": "P1",
        "priority_window_mins": 0, "assigned_department": "Emergency / Trauma",
        "message": "Emergency case registered. Doctor notified."}}

# ═══════════════════════════════════════════════════════════
# SPEECH TRANSCRIPTION (Sarvam via llm_orchestrator)
# ═══════════════════════════════════════════════════════════
@app.get("/api/transcribe/health", tags=["speech"])
def transcribe_health():
    return {
        "transcribe_available": _TRANSCRIBE_AVAILABLE,
        "transcribe_import_error": _transcribe_import_error,
        "sarvam_key_set": bool(_SARVAM_API_KEY),
        "sarvam_key_hint": (f"…{_SARVAM_API_KEY[-4:]}"
                            if _SARVAM_API_KEY else None),
        "sarvam_model": os.getenv("SARVAM_STT_MODEL", "saarika:v2"),
        "sarvam_url": os.getenv("SARVAM_STT_URL",
                                "https://api.sarvam.ai/speech-to-text"),
    }


@app.post("/api/transcribe", tags=["speech"])
async def transcribe_endpoint(
    audio: UploadFile = File(...),
    language: str = Form("en"),
):
    if not _TRANSCRIBE_AVAILABLE:
        logger.error("transcribe_audio not available: %s", _transcribe_import_error)
        raise HTTPException(
            503,
            detail=(
                "Speech transcription service unavailable. "
                f"Import error: {_transcribe_import_error}"
            ),
        )

    data = await audio.read()
    logger.info(
        "transcribe request: filename=%s size=%d bytes language=%s",
        audio.filename, len(data), language,
    )
    if not data:
        raise HTTPException(400, "Empty audio file")

    try:
        result = transcribe_audio(
            audio_bytes=data,
            filename=audio.filename or "voice.webm",
            language=language,
        )
    except Exception as exc:
        logger.exception("transcribe_audio raised")
        raise HTTPException(
            500,
            detail=f"transcribe_audio raised: {type(exc).__name__}: {exc}",
        )

    logger.info("transcribe result: source=%s error=%s text_len=%d",
                result.get("_source"), result.get("_error"),
                len(result.get("text") or ""))

    if result.get("_error") and not result.get("text"):
        raise HTTPException(
            status_code=422,
            detail=(
                f"Transcription provider error "
                f"({result.get('_source')}): {result['_error']}"
            ),
        )

    return {
        "text": result.get("text", ""),
        "original": result.get("original", ""),
        "language": result.get("language", language),
        "translated": result.get("translated", False),
        "_source": result.get("_source"),
    }

# ═══════════════════════════════════════════════════════════
# TRIAGE
# ═══════════════════════════════════════════════════════════
@app.post("/api/triage", tags=["triage"])
async def create_triage(
    req: schemas.TriageRequest,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    if not getattr(req.patient, "consent_given", False):
        raise HTTPException(400, "Informed consent is mandatory before triage.")

    v = req.vitals
    text = req.symptoms_text
    vitals_dict = _to_dict(v)
    category = req.patient.category
    req_lab_findings = getattr(req, "lab_findings", None) or {}
    image_findings = getattr(req, "image_findings", None) or ""

    merged_symptoms = text
    if image_findings:
        merged_symptoms = f"{text}\n[Image observation: {image_findings}]"

    triage_result, mews, tier = _run_triage(
        v, text, req.facility_type, category,
        age=req.patient.age, gender=req.patient.sex,
        lab_findings=req_lab_findings,
        duration=getattr(req.patient, "duration", None),
        symptom_onset=getattr(req, "symptom_onset", None),
    )

    try:
        clinical = await generate_clinical_summary(
            symptoms_text=merged_symptoms, vitals=vitals_dict,
            duration=getattr(req.patient, "duration", None),
            severity=getattr(req.patient, "severity", None),
            medical_history=getattr(req.patient, "medical_history", None),
            allergies=getattr(req.patient, "allergies", None),
            medications=getattr(req.patient, "current_medications", None),
        )
    except Exception:
        logger.exception("Clinical summary generation failed")
        clinical = {"summary": "Summary unavailable.", "timeline": [],
                    "missing_information": [], "risk_tier": tier,
                    "explanation": "", "translated_symptoms": "",
                    "_source": "error"}

    pid = (req.patient.patient_id or "").strip()
    if not pid or pid.lower() == "auto":
        pid = generate_patient_id(db)
    original_text = getattr(req, "original_transcript", None) or text
    translated_text = clinical.get("translated_symptoms") or text

    try:
        p = models.Patient(
            patient_id=pid, abha_id=req.patient.abha_id,
            age=req.patient.age, sex=req.patient.sex, name=req.patient.name,
            mobile=req.patient.mobile, email=req.patient.email,
            category=req.patient.category,
            duration_of_symptoms=getattr(req.patient, "duration", None),
            severity=getattr(req.patient, "severity", None),
            medical_history=getattr(req.patient, "medical_history", None),
            allergies=getattr(req.patient, "allergies", None),
            current_medications=getattr(req.patient, "current_medications", None),
            pregnancy_status=getattr(req.patient, "pregnancy_status", None),
            consent_given=getattr(req.patient, "consent_given", False),
        )
        db.add(p)
        db.flush()

        routing = triage_result.get("routing", {})
        assigned_department = routing.get("recommended_department", "General OPD")
        all_doctors = db.query(models.User).filter(
            models.User.role == "doctor").all()
        decision = assign_doctor(
            doctors=all_doctors,
            required_department=assigned_department,
            priority=tier,
            facility_id=getattr(user, "facility_id", None))
        chosen = decision.get("chosen_doctor")
        assigned_doctor_id = chosen.id if chosen else None
        assigned_doctor_name = chosen.full_name if chosen else "Duty Medical Officer"
        estimated_wait_mins = estimate_wait(chosen, tier) if chosen else 0
        if chosen:
            chosen.current_load += 1
            chosen.total_assigned_today += 1
            db.add(chosen)

        missing_info = (triage_result.get("identified_missing_info", [])
                        or clinical.get("missing_information", []))
        # 👈 FIXED: Prefer the exact questions the nurse saw on screen
        frontend_questions = getattr(req, "followup_questions", None) or []
        questions = frontend_questions if frontend_questions else triage_result.get("prioritized_questions", [])
        reasoning = ", ".join(triage_result.get("triage_reasoning", [])) or ""

        r = models.TriageRecord(
            patient_id=p.id, facility_id=getattr(user, "facility_id", None),
            symptoms_text=text, vitals_json=json.dumps(vitals_dict),
            mews_score=mews,
            ai_priority=triage_result.get("provisional_triage", {}).get(
                "priority_code", tier),
            priority_window_mins=10 if tier in ["P1", "P2"] else 60,
            assigned_department=assigned_department,
            assigned_doctor_id=assigned_doctor_id,
            estimated_wait_mins=estimated_wait_mins,
            ai_summary=clinical.get("summary", ""),
            ai_timeline_json=json.dumps(clinical.get("timeline", [])),
            ai_gaps_json=json.dumps(missing_info),
            ai_questions_json=json.dumps(questions),
            ai_explanation=clinical.get("explanation", reasoning),
            original_transcript=original_text,
            translated_text=translated_text,
            follow_up_answers_json=json.dumps(
                getattr(req, "followup_answers", None) or {}),
            # 👈 NEW: Save OCR & Vision to DB so doctor can view them later
            lab_extracted_json=json.dumps(getattr(req, "lab_extracted", None) or {}),
            image_observations_json=json.dumps(getattr(req, "image_observations", None) or {}),
            ai_source=clinical.get("_source", "unknown"),
            status="Waiting Review", created_by=user.id,
        )
        db.add(r)
        db.flush()

        db.add(models.AssignmentDecision(
            triage_record_id=r.id,
            chosen_doctor_id=assigned_doctor_id,
            chosen_doctor_name=assigned_doctor_name,
            chosen_doctor_department=chosen.department if chosen else None,
            total_score=int(decision.get("score", 0)),
            candidates_considered=decision.get("total_considered", 0),
            reasons_json=json.dumps(decision.get("reasons", [])),
            candidate_scores_json=json.dumps(decision.get("candidate_scores", [])),
            fallback_used=decision.get("fallback_used"),
        ))
        db.commit()
        db.refresh(r)
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Patient ID conflict")
    except SQLAlchemyError as e:
        db.rollback()
        logger.exception("Failed to persist triage record.")
        raise HTTPException(500, f"Could not save triage: {e}")

    return {"success": True, "data": {
        "record_id": r.id, "patient_id": pid, "priority": r.ai_priority,
        "priority_window_mins": r.priority_window_mins, "mews_score": mews,
        "mews_breakdown": triage_result.get("physiological_deterioration", {}).get(
            "mews_breakdown", []),
        "triage_reason": reasoning, "summary": clinical.get("summary"),
        "timeline": clinical.get("timeline", []), "identified_gaps": missing_info,
        "follow_up_questions": questions, "routing": routing,
        "ai_source": clinical.get("_source"), "status": "Waiting Review",
        "assigned_department": assigned_department,
        "assigned_doctor": {"id": assigned_doctor_id, "name": assigned_doctor_name},
        "estimated_wait_mins": estimated_wait_mins,
        "assignment_explanation": decision.get("reasons", []),
        "assignment_fallback": decision.get("fallback_used"),
        "original_transcript": original_text, "translated_text": translated_text}}

# ═══════════════════════════════════════════════════════════
# FOLLOW-UP QUESTIONS — symptom-aware (English + Odia + Hindi)
# ═══════════════════════════════════════════════════════════

_ODIA_HINDI_KEYWORDS = {
    "chest":     ["ଛାତି", "छाती", "छाति"],
    "burning":   ["ଜ୍ୱାଲୁଛି", "ଜ୍ୱାଲୁଚ୍ଛି", "ଜଳୁଛି", "जलना", "जलन"],
    "cold":      ["ଥଣ୍ଡା", "ଥଣ୍ଡ", "ठंड"],
    "eye":       ["ଆଖି", "ଆଖିରେ", "आँख", "आंख"],
    "head":      ["ମୁଣ୍ଡ", "ମୁଣ୍ଡରେ", "सिर", "सर"],
    "fever":     ["ଜ୍ୱର", "ज्वर", "बुखार"],
    "stomach":   ["ପେଟ", "ପେଟରେ", "पेट"],
    "leg":       ["ଗୋଡ଼", "ଗୋଡ", "पैर", "पांव"],
    "arm":       ["ହାତ", "हाथ", "बांह"],
    "ear":       ["କାନ", "कान"],
    "nose":      ["ନାକ", "नाक"],
    "tooth":     ["ଦାନ୍ତ", "दांत"],
    "throat":    ["ଗଳା", "गला"],
    "skin":      ["ଚର୍ମ", "त्वचा", "चमड़ी"],
    "breath":    ["ଶ୍ୱାସ", "ନିଶ୍ୱାସ", "सांस", "श्वास"],
    "vomiting":  ["ବାନ୍ତି", "उल्टी"],
    "cough":     ["କାଶ", "खांसी"],
    "wound":     ["କ୍ଷତ", "ଘାଉ", "घाव", "जख्म"],
    "pain":      ["ଯନ୍ତ୍ରଣା", "ବ୍ୟଥା", "दर्द", "पीड़ा"],
    "fracture":  ["ଭଙ୍ଗା", "हड्डी", "फ्रैक्चर"],
    "urine":     ["ପରିସ୍ରା", "ପେଶାବ", "पेशाब", "मूत्र"],
    "dizzy":     ["ଘୂରିବା", "चक्कर"],
    "rash":      ["ଦାଗ", "दाने", "चकत्ते"],
    "thorn":     ["କଣ୍ଟା", "काँटा"],
    "pus":       ["ପୂଜ", "मवाद"],
    "foot":      ["ପାଦ", "ପାଦରେ", "पैर"],
    "bleeding":  ["ରକ୍ତସ୍ରାବ", "खून", "रक्त"],
    "nausea":    ["ଅଇ", "मतली"],
    "diarrhea":  ["ଝାଡ଼ା", "दस्त"],
    "weakness":  ["ଦୁର୍ବଳତା", "कमजोरी"],
    "swelling":  ["ଫୁଲા", "सूजन"],
    "burn":      ["ପୋଡ଼ିଯିବା", "ପୋଡ଼ା", "जलना"],
    "injury":    ["ଆଘାତ", "चोट"],
}

_csv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "query.csv")
_loaded_diseases = 0

if os.path.exists(_csv_path):
    try:
        with open(_csv_path, encoding="utf-8") as _f:
            _reader = csv.DictReader(_f)
            _columns = _reader.fieldnames or []
            logger.info("query.csv columns: %s", _columns)

            for _row in _reader:
                _en = (_row.get("LabelEN") or _row.get("itemLabel_en")
                       or _row.get("English") or "").strip().lower()
                _hi = (_row.get("LabelHI") or _row.get("itemLabel_hi")
                       or _row.get("Hindi") or "").strip()
                _od = (_row.get("LabelOR") or _row.get("itemLabel_or")
                       or _row.get("Odia") or "").strip()

                if not _en or len(_en) < 3:
                    continue
                if _en not in _ODIA_HINDI_KEYWORDS:
                    _ODIA_HINDI_KEYWORDS[_en] = []
                if _hi and _hi not in _ODIA_HINDI_KEYWORDS[_en]:
                    _ODIA_HINDI_KEYWORDS[_en].append(_hi)
                if _od and _od not in _ODIA_HINDI_KEYWORDS[_en]:
                    _ODIA_HINDI_KEYWORDS[_en].append(_od)
                _loaded_diseases += 1
        logger.info("✓ Loaded %d disease terms from query.csv", _loaded_diseases)
    except Exception as _e:
        logger.warning("Could not load query.csv: %s", _e)
else:
    logger.warning("query.csv not found at %s — using only manual keywords", _csv_path)


def _detect_script(text: str) -> str:
    if not text:
        return "english"
    for c in text:
        if '\u0B00' <= c <= '\u0B7F':
            return "odia"
        if '\u0900' <= c <= '\u097F':
            return "hindi"
    return "english"


def _has_odia_hindi(text: str) -> bool:
    if not text:
        return False
    return any(
        '\u0900' <= c <= '\u097F'
        or '\u0B00' <= c <= '\u0B7F'
        for c in text
    )


def _map_odia_hindi_to_english(text: str) -> List[str]:
    found = []
    for eng, variants in _ODIA_HINDI_KEYWORDS.items():
        if any(v in text for v in variants):
            found.append(eng)
    return found


def _template_questions(category: str, symptoms_text: str = "") -> List[Dict[str, str]]:
    raw = (symptoms_text or "")
    s = raw.lower()

    if _has_odia_hindi(raw):
        hints = _map_odia_hindi_to_english(raw)
        logger.info("Odia/Hindi keywords detected: %s", hints or "(none)")
        s = (s + " " + " ".join(hints)).lower()

    if category == "Pregnancy":
        return [
            {"id": "p1", "q": "Any vaginal bleeding or fluid leakage?", "type": "yesno"},
            {"id": "p2", "q": "Any severe headache or blurred vision?", "type": "yesno"},
            {"id": "p3", "q": "How many weeks pregnant are you?", "type": "text"},
            {"id": "p4", "q": "Is the baby moving normally?", "type": "yesno"},
        ]

    if category == "Child":
        child_qs = [
            {"id": "c1", "q": "Is the child lethargic or inconsolable?", "type": "yesno"},
            {"id": "c2", "q": "Is the child refusing to feed or drink?", "type": "yesno"},
            {"id": "c3", "q": "Any convulsions or seizures?", "type": "yesno"},
        ]
        if any(k in s for k in ["fever", "temperature", "chills", "hot"]):
            child_qs.append({"id": "c_fv1", "q": "How many days has the fever lasted?", "type": "text"})
            child_qs.append({"id": "c_fv2", "q": "Any rash along with the fever?", "type": "yesno"})
        if any(k in s for k in ["cough", "breathing", "breathless", "wheeze"]):
            child_qs.append({"id": "c_b1", "q": "Is there fast breathing or chest indrawing?", "type": "yesno"})
        if any(k in s for k in ["vomit", "diarrhea", "stool", "loose"]):
            child_qs.append({"id": "c_a1", "q": "Any blood in vomit or stool?", "type": "yesno"})
            child_qs.append({"id": "c_a2", "q": "Is the child passing urine normally?", "type": "yesno"})
        if any(k in s for k in ["rash", "skin", "itch"]):
            child_qs.append({"id": "c_sk1", "q": "Where on the body is the rash located?", "type": "text"})
        child_qs.append({"id": "c_dyn", "q": f"Can you describe the {s[:30]}... in more detail?", "type": "text"})
        return child_qs

    if any(k in s for k in ["fracture", "bone", "broken", "leg", "arm", "wrist", "ankle", "sprain"]):
        return [
            {"id": "f1", "q": "Can the patient bear weight or use the limb?", "type": "yesno"},
            {"id": "f2", "q": "Is there visible deformity, swelling, or bruising?", "type": "yesno"},
            {"id": "f3", "q": "Did the injury involve a fall or accident?", "type": "yesno"},
            {"id": "f4", "q": "Is there numbness, tingling, or loss of movement?", "type": "yesno"},
            {"id": "f5", "q": "When exactly did the injury happen?", "type": "text"},
        ]

    if any(k in s for k in ["head injury", "head trauma", "hit head", "skull", "concussion"]):
        return [
            {"id": "h1", "q": "Was there any loss of consciousness?", "type": "yesno"},
            {"id": "h2", "q": "Any vomiting after the injury?", "type": "yesno"},
            {"id": "h3", "q": "Any bleeding from ears, nose, or wound?", "type": "yesno"},
            {"id": "h4", "q": "Any confusion, memory loss, or drowsiness?", "type": "yesno"},
            {"id": "h5", "q": "When did the injury occur?", "type": "text"},
        ]

    if any(k in s for k in ["chest", "heart", "cardiac", "palpitation", "burning"]):
        return [
            {"id": "ch1", "q": "Is the chest pain or burning radiating to arm, jaw, or back?", "type": "yesno"},
            {"id": "ch2", "q": "Associated with sweating, nausea, or breathlessness?", "type": "yesno"},
            {"id": "ch3", "q": "Is it worse on exertion, after meals, or at rest?", "type": "text"},
            {"id": "ch4", "q": "Any history of heart disease, diabetes, or hypertension?", "type": "yesno"},
        ]

    if any(k in s for k in ["breathing", "breathless", "shortness", "wheeze", "asthma", "cough"]):
        return [
            {"id": "b1", "q": "Is the difficulty at rest or only on exertion?", "type": "text"},
            {"id": "b2", "q": "Any fever, cough, or sputum production?", "type": "yesno"},
            {"id": "b3", "q": "Any wheeze or noisy breathing?", "type": "yesno"},
            {"id": "b4", "q": "Any known asthma or COPD?", "type": "yesno"},
        ]

    if any(k in s for k in ["fever", "temperature", "chills", "rigor", "hot"]):
        return [
            {"id": "fv1", "q": "How many days has the fever lasted?", "type": "text"},
            {"id": "fv2", "q": "Any rash along with the fever?", "type": "yesno"},
            {"id": "fv3", "q": "Any body ache, joint pain, or headache?", "type": "yesno"},
            {"id": "fv4", "q": "Any recent travel to a malaria or dengue area?", "type": "yesno"},
        ]

    if any(k in s for k in ["cold", "runny", "sneez", "congestion"]):
        return [
            {"id": "cl1", "q": "How many days have the cold symptoms lasted?", "type": "text"},
            {"id": "cl2", "q": "Any fever, body ache, or sore throat?", "type": "yesno"},
            {"id": "cl3", "q": "Any difficulty breathing or chest tightness?", "type": "yesno"},
            {"id": "cl4", "q": "Any known allergies or asthma?", "type": "yesno"},
        ]

    if any(k in s for k in ["eye", "vision"]):
        return [
            {"id": "ey1", "q": "Any redness, discharge, or swelling in the eye?", "type": "yesno"},
            {"id": "ey2", "q": "Any blurred or double vision?", "type": "yesno"},
            {"id": "ey3", "q": "Is the problem one-sided or both eyes?", "type": "text"},
            {"id": "ey4", "q": "Any recent injury or foreign body exposure?", "type": "yesno"},
        ]

    if any(k in s for k in ["wound", "thorn", "pus", "infection", "abscess",
                             "cut", "swelling", "foot", "sprain"]):
        return [
            {"id": "w1", "q": "Where exactly is the wound — foot, leg, hand, or other?", "type": "text"},
            {"id": "w2", "q": "Is there visible pus, discharge, or a foul smell?", "type": "yesno"},
            {"id": "w3", "q": "Is the area red, hot, or swollen?", "type": "yesno"},
            {"id": "w4", "q": "Any fever, chills, or red streaks spreading from the wound?", "type": "yesno"},
            {"id": "w5", "q": "Was the wound caused by a thorn, animal, or rusty object?", "type": "yesno"},
            {"id": "w6", "q": "Has the patient had a tetanus shot in the last 5 years?", "type": "yesno"},
        ]

    if any(k in s for k in ["skin", "rash", "itch", "burn", "boil", "lesion"]):
        return [
            {"id": "sk1", "q": "Where on the body is the affected area?", "type": "text"},
            {"id": "sk2", "q": "Is there pain, discharge, or bleeding?", "type": "yesno"},
            {"id": "sk3", "q": "How long has it been present?", "type": "text"},
            {"id": "sk4", "q": "Any fever or spreading redness?", "type": "yesno"},
        ]

    if any(k in s for k in ["abdominal", "stomach", "belly", "vomit", "nausea",
                             "diarrhea", "loose motion"]):
        return [
            {"id": "a1", "q": "Any vomiting or diarrhea? How many times?", "type": "text"},
            {"id": "a2", "q": "Any blood in vomit or stool?", "type": "yesno"},
            {"id": "a3", "q": "Is the pain in a specific area (upper/lower/right/left)?", "type": "text"},
            {"id": "a4", "q": "Any fever or dehydration?", "type": "yesno"},
        ]

    if any(k in s for k in ["urine", "urinary", "dysuria", "frequency"]):
        return [
            {"id": "u1", "q": "Any burning or pain while passing urine?", "type": "yesno"},
            {"id": "u2", "q": "Any blood in the urine?", "type": "yesno"},
            {"id": "u3", "q": "Any fever, flank, or back pain?", "type": "yesno"},
            {"id": "u4", "q": "How many days have symptoms lasted?", "type": "text"},
        ]

    if any(k in s for k in ["headache", "migraine", "head pain", "head"]):
        return [
            {"id": "hd1", "q": "Any vision changes, nausea, or vomiting?", "type": "yesno"},
            {"id": "hd2", "q": "Is the headache one-sided or generalized?", "type": "text"},
            {"id": "hd3", "q": "Any neck stiffness or sensitivity to light?", "type": "yesno"},
            {"id": "hd4", "q": "How long have you had this headache?", "type": "text"},
        ]

    if any(k in s for k in ["dizzy", "vertigo", "giddiness", "blackout", "faint"]):
        return [
            {"id": "dz1", "q": "Any loss of consciousness or fall?", "type": "yesno"},
            {"id": "dz2", "q": "Is it worse on standing up or moving head?", "type": "yesno"},
            {"id": "dz3", "q": "Any vomiting, hearing loss, or ear ringing?", "type": "yesno"},
            {"id": "dz4", "q": "How long do episodes last?", "type": "text"},
        ]

    return [
        {"id": "g1", "q": "How long have the symptoms lasted?", "type": "text"},
        {"id": "g2", "q": "Severity of symptoms?", "type": "severity"},
        {"id": "g3", "q": "Any fever, vomiting, or difficulty breathing?", "type": "yesno"},
        {"id": "g4", "q": "Any known allergies or current medications?", "type": "text"},
    ]


@app.post("/api/triage/preview-follow-ups", tags=["triage"])
async def preview_follow_ups(
    payload: dict,
    user: models.User = Depends(get_current_user),
):
    symptoms = (payload.get("symptoms_text") or "").strip()
    age = payload.get("age", 30)
    category = payload.get("category", "None")

    if not symptoms:
        return {"success": True, "source": "empty",
                "questions": _template_questions(category, "")}

    is_indic = _has_odia_hindi(symptoms)
    detected_lang = _detect_script(symptoms)
    logger.info(
        "preview_follow_ups: symptoms=%r, lang=%s, groq=%s",
        symptoms[:60], detected_lang, "ready" if groq_client else "unavailable"
    )

    if groq_client is not None:
        try:
            lang_instruction = {
                "odia":    "Odia (ଓଡ଼ିଆ script)",
                "hindi":   "Hindi (Devanagari / हिन्दी script)",
                "english": "English",
            }[detected_lang]

            prompt = f"""You are a triage nurse assistant at a rural Indian clinic.

The patient's symptoms are written in {lang_instruction}:
"{symptoms}"

Age: {age}, Category: {category}

TASK:
1. Understand the symptoms (internally translate to English if needed).
2. Generate 4-5 TARGETED follow-up questions SPECIFIC to the complaint.
3. **CRITICAL: Write ALL question text in {lang_instruction}.**
   - If the patient wrote in Odia, EVERY question MUST be in Odia script.
   - If the patient wrote in Hindi, EVERY question MUST be in Devanagari.
   - If the patient wrote in English, write in English.
   Do NOT mix languages.
4. Focus on red-flag symptoms and clarifications that change triage priority.
5. **Do NOT just ask generic questions about the category.** If the patient is a child with a fever, ask about the fever (duration, rash), not just generic child questions.
6. Do NOT ask generic questions like "how long symptoms lasted" unless nothing else applies.

Return ONLY a JSON array (no markdown, no explanation):
[
  {{"id": "q1", "q": "<question in {lang_instruction}>", "type": "yesno"}},
  {{"id": "q2", "q": "<question in {lang_instruction}>", "type": "text"}},
  {{"id": "q3", "q": "<question in {lang_instruction}>", "type": "severity"}}
]

"type" MUST be one of: "yesno", "text", "severity".
Return ONLY the JSON array."""

            resp = groq_client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3, max_tokens=800,
            )
            text = resp.choices[0].message.content.strip()
            for fence in ("```json", "```JSON", "```"):
                if text.startswith(fence):
                    text = text[len(fence):]
            if text.endswith("```"):
                text = text[:-3]

            questions = json.loads(text.strip())
            cleaned = []
            for q in questions:
                if not isinstance(q, dict):
                    continue
                qid = q.get("id") or f"q{len(cleaned)+1}"
                qt = q.get("q") or q.get("text") or ""
                ty = q.get("type", "text")
                if ty not in ("yesno", "text", "severity"):
                    ty = "text"
                if qt:
                    cleaned.append({"id": qid, "q": qt, "type": ty})

            if cleaned:
                logger.info("✓ Groq generated %d follow-ups in %s",
                            len(cleaned), detected_lang)
                return {"success": True,
                        "source": f"groq/{GROQ_MODEL}",
                        "language": detected_lang,
                        "questions": cleaned}
            logger.warning("Groq returned empty question list")

        except Exception as exc:
            logger.exception("Groq follow-up generation failed: %s", exc)

    logger.warning("Using symptom-aware English fallback")
    return {
        "success": True,
        "source": "template_smart" if is_indic else "template_english",
        "language": "english",
        "questions": _template_questions(category, symptoms),
    }

# ═══════════════════════════════════════════════════════════
# OFFLINE SYNC
# ═══════════════════════════════════════════════════════════
@app.post("/api/sync/upload", tags=["sync"])
async def sync_offline_records(
    batch: List[dict],
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    synced = 0
    for item in batch:
        try:
            p = db.query(models.Patient).filter(
                models.Patient.patient_id == item.get("patient_id")).first()
            if not p:
                p = models.Patient(
                    patient_id=item.get("patient_id", generate_patient_id(db)),
                    name=item.get("name", "Offline Patient"),
                    age=item.get("age"), sex=item.get("sex"),
                    category=item.get("category", "None"),
                    allergies=item.get("allergies"),
                    medical_history=item.get("medical_history"),
                    consent_given=item.get("consent_given", False))
                db.add(p)
                db.flush()
            db.add(models.TriageRecord(
                patient_id=p.id, symptoms_text=item.get("symptoms_text"),
                vitals_json=json.dumps(item.get("vitals", {})),
                original_transcript=item.get("original_transcript"),
                translated_text=item.get("translated_text"),
                status="PENDING_AI", created_by=user.id,
                facility_id=getattr(user, "facility_id", None)))
            synced += 1
        except Exception as e:
            logger.error(f"Failed to sync offline record: {e}")
            db.rollback()
            continue
    db.commit()
    return {"success": True, "synced": synced, "message": "AI processing queued"}

# ═══════════════════════════════════════════════════════════
# FOLLOW-UP (record-based)
# ═══════════════════════════════════════════════════════════
@app.post("/api/triage/{record_id}/generate-follow-ups", tags=["triage"])
def generate_follow_ups(
    record_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    record = db.query(models.TriageRecord).filter(
        models.TriageRecord.id == record_id).first()
    if not record:
        raise HTTPException(404, "Not found")
    patient = db.query(models.Patient).filter(
        models.Patient.id == record.patient_id).first()
    category = patient.category if patient else "None"
    qs = _template_questions(category, record.symptoms_text or "")
    record.ai_questions_json = json.dumps(qs)
    db.commit()
    return {"success": True, "category_used": category, "follow_up_questions": qs}

@app.patch("/api/triage/{record_id}/follow-up-answers", tags=["triage"])
def save_follow_up_answers(
    record_id: int,
    req: schemas.FollowUpAnswersRequest,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    record = db.query(models.TriageRecord).filter(
        models.TriageRecord.id == record_id).first()
    if not record:
        raise HTTPException(404, "Not found")
    record.follow_up_answers_json = json.dumps(req.answers)
    db.commit()
    return {"success": True, "answers": req.answers}

# ═══════════════════════════════════════════════════════════
# MANUAL ASSIGNMENT
# ═══════════════════════════════════════════════════════════
@app.patch("/api/triage/{record_id}/assign", tags=["triage"])
def manual_assignment(
    record_id: int,
    req: schemas.DecisionRequest,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_doctor),
):
    record = db.query(models.TriageRecord).filter(
        models.TriageRecord.id == record_id).first()
    if not record:
        raise HTTPException(404, "Not found")
    old_dept = record.assigned_department
    if req.assigned_department:
        record.assigned_department = req.assigned_department
    if req.assigned_doctor_id:
        record.assigned_doctor_id = req.assigned_doctor_id
    record.is_manually_assigned = True
    db.add(models.AuditLog(user_id=user.id, record_id=record.id,
                           action="MANUAL_ASSIGN",
                           details=f"Changed dept from {old_dept} to {req.assigned_department}"))
    db.commit()
    return {"success": True, "assigned_department": record.assigned_department,
            "assigned_doctor_id": record.assigned_doctor_id,
            "is_manually_assigned": record.is_manually_assigned}

# ═══════════════════════════════════════════════════════════
# QUEUE
# ═══════════════════════════════════════════════════════════
@app.get("/api/queue", tags=["queue"])
def get_queue(
    limit: int = 100, offset: int = 0,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    limit = max(1, min(limit, 500))
    offset = max(0, offset)
    order = {"P1": 0, "P2": 1, "P3": 2, "P4": 3}
    records = db.query(models.TriageRecord).filter(
        models.TriageRecord.status.in_(
            ["Waiting Review", "PENDING_AI", "In OPD Treatment", "Admitted"])).all()
    records.sort(key=lambda r: order.get(r.ai_priority, 99))
    total = len(records)
    page = records[offset: offset + limit]
    patients = _fetch_patients_map(db, [r.patient_id for r in page])
    queue = []
    for r in page:
        p = patients.get(r.patient_id)
        queue.append({
            "record_id": r.id,
            "patient_id": p.patient_id if p else "UNKNOWN",
            "demographics": f"{p.age}y / {p.sex}" if p else "N/A",
            "priority": r.ai_priority,
            "priority_window_mins": r.priority_window_mins,
            "assigned_department": r.assigned_department,
            "mews": r.mews_score,
            "symptoms": (r.symptoms_text or "")[:120],
            "status": r.status,
            "allergies": p.allergies if p else "None"})
    return {"success": True, "data": {
        "metrics": {"total_active": total,
                    "p1": sum(1 for r in records if r.ai_priority == "P1"),
                    "p2": sum(1 for r in records if r.ai_priority == "P2")},
        "pagination": {"limit": limit, "offset": offset, "total": total},
        "queue": queue}}

@app.post("/api/queue/{patient_id}/review", tags=["queue"])
def mark_as_reviewed(
    patient_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    record = db.query(models.TriageRecord).filter(
        models.TriageRecord.id == patient_id).first()
    if not record:
        raise HTTPException(404, "Record not found")
    record.status = "Reviewed"
    db.add(models.AuditLog(user_id=user.id, record_id=record.id,
                           action="MARKED_REVIEWED",
                           details=f"Record {patient_id} reviewed"))
    db.commit()
    return {"status": "success", "message": f"Record {patient_id} marked reviewed"}

@app.get("/api/queue/me/{patient_id}", tags=["queue"])
def patient_queue_position(
    patient_id: str,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    order = {"P1": 0, "P2": 1, "P3": 2, "P4": 3}
    wait_per_tier = {"P1": 5, "P2": 30, "P3": 60, "P4": 120}
    patient = db.query(models.Patient).filter(
        models.Patient.patient_id == patient_id).first()
    if not patient:
        raise HTTPException(404, "Patient not found")
    records = db.query(models.TriageRecord).filter(
        models.TriageRecord.status == "Waiting Review").all()
    records.sort(key=lambda r: order.get(r.ai_priority, 99))
    pos = None; my_r = None
    for i, r in enumerate(records):
        if r.patient_id == patient.id:
            pos = i + 1; my_r = r; break
    if not my_r or pos is None:
        raise HTTPException(404, "Patient not in active queue")
    if getattr(user, "facility_id", None) and my_r.facility_id != user.facility_id:
        raise HTTPException(403, "Not allowed")
    ahead = records[:pos - 1]
    wait = sum(wait_per_tier.get(r.ai_priority, 60) for r in ahead)
    return {"success": True, "data": {
        "patient_id": patient_id, "position_in_queue": pos,
        "total_in_queue": len(records), "patients_ahead": pos - 1,
        "estimated_wait_minutes": wait, "status": my_r.status}}

# ═══════════════════════════════════════════════════════════
# GET ONE RECORD
# ═══════════════════════════════════════════════════════════
@app.get("/api/triage/{record_id}", tags=["triage"])
def get_triage(
    record_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    r = db.query(models.TriageRecord).filter(
        models.TriageRecord.id == record_id).first()
    if not r:
        raise HTTPException(404, "Not found")
    p = db.query(models.Patient).filter(
        models.Patient.id == r.patient_id).first()
    return {"success": True, "data": {
        "record_id": r.id,
        "patient": {"name": p.name if p else "Unknown",
                    "age": p.age if p else None,
                    "sex": p.sex if p else None,
                    "mobile": p.mobile if p else None,
                    "category": p.category if p else "None",
                    "allergies": p.allergies if p else None,
                    "medical_history": p.medical_history if p else None,
                    "medications": p.current_medications if p else None},
        "symptoms_text": r.symptoms_text,
        "vitals": _safe_json_loads(r.vitals_json, {}),
        "mews_score": r.mews_score, "ai_priority": r.ai_priority,
        "final_priority": r.final_priority,
        "priority_window_mins": r.priority_window_mins,
        "assigned_department": r.assigned_department,
        "assigned_doctor_id": r.assigned_doctor_id,
        "estimated_wait_mins": r.estimated_wait_mins,
        "is_manually_assigned": r.is_manually_assigned,
        "summary": r.ai_summary,
        "timeline": _safe_json_loads(r.ai_timeline_json, []),
        "identified_gaps": _safe_json_loads(r.ai_gaps_json, []),
        "ai_explanation": r.ai_explanation,
        "follow_up_questions": _safe_json_loads(r.ai_questions_json, []),
        "follow_up_answers": _safe_json_loads(r.follow_up_answers_json, {}),
        "original_transcript": r.original_transcript,
        "translated_text": r.translated_text,
        "lab_extracted": _safe_json_loads(r.lab_extracted_json, {}),
        "image_observations": _safe_json_loads(r.image_observations_json, {}),
        "ai_source": r.ai_source, "status": r.status,
        "clinical_notes": r.clinical_notes,
        "created_at": r.created_at.isoformat() if r.created_at else None,
        "reviewed_at": r.reviewed_at.isoformat() if r.reviewed_at else None,
    }}

# ═══════════════════════════════════════════════════════════
# REFERRAL NOTE
# ═══════════════════════════════════════════════════════════
@app.get("/api/triage/{record_id}/referral-note", tags=["triage"])
def generate_referral_note(
    record_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    r = db.query(models.TriageRecord).filter(
        models.TriageRecord.id == record_id).first()
    if not r:
        raise HTTPException(404, "Not found")
    p = db.query(models.Patient).filter(
        models.Patient.id == r.patient_id).first()
    latest = db.query(models.ReferralDecision).filter(
        models.ReferralDecision.triage_case_id == record_id).order_by(
        models.ReferralDecision.id.desc()).first()
    dest_service = "General Medicine"
    dest_facility = "District Hospital"
    if latest:
        dest_service = latest.final_service or latest.suggested_service
        if latest.final_facility_id:
            fac = db.query(models.Facility).filter(
                models.Facility.id == latest.final_facility_id).first()
            if fac:
                dest_facility = fac.facility_name
    timeline = _safe_json_loads(r.ai_timeline_json, [])
    gaps = _safe_json_loads(r.ai_gaps_json, [])
    note = f"""
========================================================
             REFERRAL NOTE — AAROGYATRIAGE
========================================================
Generated: {_utcnow().strftime('%Y-%m-%d %H:%M UTC')}
Record ID: {r.id}

--- PATIENT ---
Name     : {p.name if p else 'Unknown'}
Age / Sex: {p.age if p else '?'}y / {p.sex if p else '?'}
Patient ID: {p.patient_id if p else '?'}

--- CLINICAL SAFETY ---
Allergies       : {p.allergies if p else 'None reported'}
Medications     : {p.current_medications if p else 'None reported'}
Medical History : {p.medical_history if p else 'None reported'}

--- PRESENTING COMPLAINT ---
{r.symptoms_text}

--- AI TRIAGE SUMMARY ---
{r.ai_summary or 'Not available'}

--- PRIORITY ---
{r.ai_priority} — Review within {r.priority_window_mins} minutes

--- TIMELINE ---
{chr(10).join(['- ' + str(t) for t in timeline]) or '- Not available'}

--- MISSING INFORMATION ---
{chr(10).join(['- ' + str(g) for g in gaps]) or '- None identified'}

--- REFERRAL DESTINATION ---
Service : {dest_service}
Facility: {dest_facility}

--- REVIEWER REMARKS ---
{r.clinical_notes or 'No additional notes.'}

--------------------------------------------------------
*Non-diagnostic. Must be verified by a licensed clinician.*
========================================================
    """.strip()
    r.referral_note = note
    db.commit()
    return {"success": True, "referral_note": note}

# ═══════════════════════════════════════════════════════════
# DOCTOR DECISION (Simple)
# ═══════════════════════════════════════════════════════════
@app.post("/api/triage/{record_id}/decision", tags=["triage"])
def doctor_decision(
    record_id: int,
    req: schemas.DecisionRequest,
    db: Session = Depends(get_db),
    doctor: models.User = Depends(require_doctor),
):
    if req.final_priority not in {"P1", "P2", "P3", "P4"}:
        raise HTTPException(422, "final_priority must be P1–P4")
    r = db.query(models.TriageRecord).filter(
        models.TriageRecord.id == record_id).first()
    if not r:
        raise HTTPException(404, "Not found")
    if r.status == "Reviewed":
        raise HTTPException(409, "Record already reviewed")
    old = r.ai_priority
    try:
        if r.assigned_doctor_id and r.assigned_doctor_id != doctor.id:
            _prev = db.query(models.User).filter(
                models.User.id == r.assigned_doctor_id).first()
            if _prev and _prev.current_load > 0:
                _prev.current_load -= 1
                db.add(_prev)
        r.final_priority = req.final_priority
        r.doctor_decision = req.decision
        r.clinical_notes = req.clinical_notes
        r.reviewed_by = doctor.id
        r.reviewed_at = _utcnow()
        if req.action == "opd":
            r.status = "In OPD Treatment"
            r.assigned_doctor_id = doctor.id
            r.assigned_department = doctor.department or r.assigned_department
        elif req.action == "admit":
            r.status = "Admitted"
            r.assigned_doctor_id = doctor.id
        elif req.action == "refer":
            r.status = "Referred"
            r.assigned_doctor_id = None
        else:
            r.status = "Reviewed"
        if req.assigned_department:
            r.assigned_department = req.assigned_department
            r.is_manually_assigned = True
        if req.assigned_doctor_id:
            r.assigned_doctor_id = req.assigned_doctor_id
        db.add(models.AuditLog(
            user_id=doctor.id, record_id=r.id, action="DOCTOR_DECISION",
            details=f"Decision: {req.decision}. Action: {req.action}. Priority: {old} -> {req.final_priority}"))
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(500, "Could not save decision")
    return {"success": True, "data": {"record_id": r.id,
            "final_priority": r.final_priority, "status": r.status}}

# ═══════════════════════════════════════════════════════════
# DOCTOR DECISION (Full)
# ═══════════════════════════════════════════════════════════
@app.post("/api/doctor/decision-full", tags=["doctor"])
def doctor_decision_full(
    req: schemas.DoctorDecisionWithMeds,
    db: Session = Depends(get_db),
    doctor: models.User = Depends(require_doctor),
):
    record = db.query(models.TriageRecord).filter(
        models.TriageRecord.id == req.patient_id).first()
    if not record:
        raise HTTPException(404, "Triage record not found")
    patient = db.query(models.Patient).filter(
        models.Patient.id == record.patient_id).first()
    token = req.token or (patient.patient_id if patient else f"T-{record.id}")
    old_priority = record.ai_priority
    response = {"status": "success", "action_taken": req.action,
                "token": token, "prescription_ready": False}
    action = {"opd": "Send to OPD", "admit": "Send to ICU",
              "refer": "Refer to DH"}.get(req.action, req.action)
    try:
        if record.assigned_doctor_id and record.assigned_doctor_id != doctor.id:
            _prev = db.query(models.User).filter(
                models.User.id == record.assigned_doctor_id).first()
            if _prev and _prev.current_load > 0:
                _prev.current_load -= 1
                db.add(_prev)
        record.final_priority = req.final_priority
        record.doctor_decision = req.decision
        record.clinical_notes = req.clinical_notes
        record.reviewed_by = doctor.id
        record.reviewed_at = _utcnow()
        if action == "Send to OPD":
            record.status = "In OPD Treatment"
            record.assigned_doctor_id = doctor.id
            response["message"] = f"Patient {token} sent to OPD"
        elif action == "Send to Chemist":
            record.status = "Prescription Pending"
            record.assigned_doctor_id = doctor.id
            code = f"RX-{_utcnow().strftime('%Y%m%d')}-{record.id:04d}"
            db.add(models.Prescription(
                prescription_code=code, triage_case_id=record.id,
                patient_id=record.patient_id, token=token, doctor_id=doctor.id,
                doctor_name=doctor.full_name,
                medicines_json=json.dumps([m.model_dump() for m in req.medicines]),
                clinical_notes=req.clinical_notes, status="pending"))
            response["prescription_ready"] = True
            response["prescription_code"] = code
            response["message"] = f"Prescription {code} created for Token {token}"
        elif action == "Refer to DH":
            record.status = "Referred"
            record.assigned_doctor_id = None
            response["referral_id"] = f"REF-{_utcnow().strftime('%Y%m%d')}-{record.id:04d}"
            response["message"] = f"Patient {token} referred to District Hospital"
        elif action == "Send to ICU":
            record.status = "In ICU"
            record.assigned_doctor_id = doctor.id
            db.add(models.ICUAdmission(
                triage_case_id=record.id, patient_id=record.patient_id,
                token=token, priority=req.final_priority, notes=req.clinical_notes,
                vitals_history_json="[]", status="active"))
            response["message"] = f"Patient {token} admitted to ICU"
        db.add(models.AuditLog(
            user_id=doctor.id, record_id=record.id,
            action="DOCTOR_DECISION_FULL",
            details=json.dumps({"decision": req.decision, "action": action,
                "old_priority": old_priority, "new_priority": req.final_priority,
                "medicines_count": len(req.medicines)})))
        db.commit()
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(500, str(e))
    return response

# ═══════════════════════════════════════════════════════════
# ICU
# ═══════════════════════════════════════════════════════════
@app.post("/api/icu/re-triage/{token}", tags=["icu"])
async def icu_re_triage(
    token: str,
    data: dict,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    token = token.strip().upper()
    icu = db.query(models.ICUAdmission).filter(
        models.ICUAdmission.token == token,
        models.ICUAdmission.status == "active").first()
    if not icu:
        raise HTTPException(404, f"Token {token} not in ICU")
    nv = data.get("vitals", {})
    ns = data.get("symptoms", [])
    lf = data.get("lab_findings", {})
    nr = run_triage_assessment({"demographics": {"age": 30, "gender": "Unknown"},
        "vitals": nv, "symptoms": ns, "lab_findings": lf,
        "patient_category": "Adult", "facility": "ICU"})
    nm = nr.get("physiological_deterioration", {}).get("mews_score", 0)
    np_ = nr.get("provisional_triage", {}).get("priority_code", "P3")
    history = _safe_json_loads(icu.vitals_history_json, [])
    history.append({"timestamp": _utcnow().isoformat(), "mews_score": nm,
                    "triage_priority": np_, "vitals": nv})
    icu.vitals_history_json = json.dumps(history)
    icu.priority = np_
    trend = "stable"
    if len(history) >= 2:
        om = history[-2]["mews_score"]
        if nm > om:
            trend = "deteriorating"
        elif nm < om:
            trend = "improving"
    dr = False
    if len(history) >= 3 and all(h["mews_score"] <= 1 for h in history[-3:]):
        dr = True
    db.add(models.AuditLog(user_id=user.id, record_id=icu.triage_case_id,
                           action="ICU_RETRIAGE",
                           details=f"Token {token}: MEWS {nm}, Trend: {trend}"))
    db.commit()
    return {"status": "success", "token": token, "new_mews": nm,
            "new_priority": np_, "trend": trend, "discharge_ready": dr,
            "recommendation": ("Discharge ready — shift to ward" if dr
                else "Deteriorating — alert doctor immediately" if trend == "deteriorating"
                else "Improving — continue monitoring" if trend == "improving"
                else "Stable — continue monitoring")}

@app.get("/api/icu/queue", tags=["icu"])
def get_icu_queue(
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    admissions = db.query(models.ICUAdmission).filter(
        models.ICUAdmission.status == "active").all()
    q = []
    for a in admissions:
        p = db.query(models.Patient).filter(
            models.Patient.id == a.patient_id).first()
        q.append({"id": a.id, "token": a.token,
                  "patient_name": p.name if p else "Unknown",
                  "age_gender": f"{p.age}/{p.sex}" if p else "N/A",
                  "priority": a.priority, "notes": a.notes,
                  "vitals_history": _safe_json_loads(a.vitals_history_json, []),
                  "admitted_at": a.admitted_at.isoformat() if a.admitted_at else None})
    return {"total_patients": len(q), "queue": q}

# ═══════════════════════════════════════════════════════════
# CHEMIST
# ═══════════════════════════════════════════════════════════
@app.get("/api/chemist/prescription/{token}", tags=["chemist"])
def get_prescription_by_token(
    token: str,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    token = token.strip().upper()
    presc = db.query(models.Prescription).filter(
        models.Prescription.token == token).first()
    if not presc:
        raise HTTPException(404, f"No prescription for Token: {token}")
    p = db.query(models.Patient).filter(
        models.Patient.id == presc.patient_id).first()
    payload = {"prescription_id": presc.id,
               "prescription_code": presc.prescription_code,
               "token": presc.token, "patient_name": p.name if p else "N/A",
               "age_gender": f"{p.age} / {p.sex}" if p else "N/A",
               "abha_id": p.abha_id if p else "N/A",
               "doctor_name": presc.doctor_name,
               "medicines": _safe_json_loads(presc.medicines_json, []),
               "clinical_notes": presc.clinical_notes, "status": presc.status,
               "created_at": presc.created_at.isoformat() if presc.created_at else None}
    if presc.status == "dispensed":
        payload["dispensed_at"] = presc.dispensed_at.isoformat() if presc.dispensed_at else None
        payload["chemist_name"] = presc.chemist_name
        return {"status": "already_dispensed",
                "message": f"Token {token} already dispensed",
                "prescription": payload}
    return {"status": "success", "token": token, "prescription": payload}

@app.post("/api/chemist/dispense", tags=["chemist"])
def dispense_medicine(
    req: schemas.ChemistDispenseInput,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    token = req.token.strip().upper()
    presc = db.query(models.Prescription).filter(
        models.Prescription.token == token).first()
    if not presc:
        raise HTTPException(404, f"Token {token} not found")
    if presc.status == "dispensed":
        raise HTTPException(400, f"Token {token} already dispensed")
    presc.status = "dispensed"
    presc.chemist_name = req.chemist_name
    presc.dispensed_at = _utcnow()
    presc.dispensed_items_json = json.dumps([d.model_dump() for d in req.dispensed_items])
    presc.out_of_stock_items_json = json.dumps(req.out_of_stock_items)
    db.add(models.AuditLog(user_id=user.id, record_id=presc.triage_case_id,
                           action="PRESCRIPTION_DISPENSED",
                           details=f"Token {token} dispensed by {req.chemist_name}"))
    db.commit()
    return {"status": "success",
            "message": f"Prescription for Token {token} dispensed",
            "token": token, "chemist_name": req.chemist_name,
            "dispensed_at": presc.dispensed_at.isoformat(), "print_ready": True}

@app.get("/api/chemist/print/{token}", tags=["chemist"])
def print_prescription(
    token: str,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    token = token.strip().upper()
    presc = db.query(models.Prescription).filter(
        models.Prescription.token == token).first()
    if not presc:
        raise HTTPException(404, f"Token {token} not found")
    if presc.status != "dispensed":
        raise HTTPException(400, "Prescription not yet dispensed")
    p = db.query(models.Patient).filter(
        models.Patient.id == presc.patient_id).first()
    return {"header": {"facility": "AarogyaTriage — Primary Health Centre",
                       "date": _utcnow().strftime("%d-%b-%Y"),
                       "token": token,
                       "prescription_code": presc.prescription_code},
            "patient": {"name": p.name if p else "N/A",
                        "age_gender": f"{p.age} / {p.sex}" if p else "N/A",
                        "abha_id": p.abha_id if p else "N/A"},
            "doctor": {"name": presc.doctor_name},
            "clinical_notes": presc.clinical_notes,
            "medicines": _safe_json_loads(presc.dispensed_items_json, []),
            "out_of_stock": _safe_json_loads(presc.out_of_stock_items_json, []),
            "chemist": {"name": presc.chemist_name,
                        "dispensed_at": presc.dispensed_at.isoformat() if presc.dispensed_at else None},
            "disclaimer": "Digitally dispensed. Non-diagnostic."}

@app.get("/api/chemist/stats", tags=["chemist"])
def get_chemist_stats(
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    today = _utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    return {"pending_prescriptions": db.query(models.Prescription).filter(
                models.Prescription.status == "pending").count(),
            "dispensed_today": db.query(models.Prescription).filter(
                models.Prescription.status == "dispensed",
                models.Prescription.dispensed_at >= today).count(),
            "total_prescriptions": db.query(models.Prescription).count()}

# ═══════════════════════════════════════════════════════════
# ADMIN
# ═══════════════════════════════════════════════════════════
_VALID_ROLES = {"doctor", "admin", "nurse", "reception", "chemist"}

@app.post("/api/admin/create-user", tags=["admin"])
def admin_create_user(
    username: str = Form(..., min_length=3, max_length=64),
    password: str = Form(..., min_length=6, max_length=128),
    role: str = Form(...),
    full_name: str = Form(..., min_length=1, max_length=120),
    facility_id: str = Form("FAC-001", max_length=64),
    department: Optional[str] = Form(None, max_length=64),
    db: Session = Depends(get_db),
    admin: models.User = Depends(require_admin),
):
    if role not in _VALID_ROLES:
        raise HTTPException(422, f"role must be one of {sorted(_VALID_ROLES)}")
    if db.query(models.User).filter(models.User.username == username).first():
        raise HTTPException(400, "Username already exists")
    try:
        db.add(models.User(
            username=username, password_hash=hash_password(password),
            role=role, full_name=full_name, facility_id=facility_id,
            department=department))
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(400, "Username exists")
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(500, "Could not create user")
    return {"success": True, "message": f"User {username} created"}

# ═══════════════════════════════════════════════════════════
# REFERRAL
# ═══════════════════════════════════════════════════════════
@app.get("/api/referral/recommend/{record_id}", tags=["referral"])
def get_referral_recommendation(
    record_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    r = db.query(models.TriageRecord).filter(
        models.TriageRecord.id == record_id).first()
    if not r:
        raise HTTPException(404, "Triage record not found")
    p = db.query(models.Patient).filter(
        models.Patient.id == r.patient_id).first()
    facilities = db.query(models.Facility).all()
    fl = [{"id": f.id, "facility_code": f.facility_code,
           "facility_name": f.facility_name, "facility_type": f.facility_type,
           "emergency_capable": f.emergency_capable,
           "operational_status": f.operational_status} for f in facilities]
    cm = {}
    for cap in db.query(models.FacilityCapability).all():
        cm.setdefault(cap.facility_id, []).append({
            "service_code": cap.service_code,
            "capability_level": cap.capability_level,
            "availability_status": cap.availability_status})
    vd = json.loads(r.vitals_json) if r.vitals_json else {}
    rec = recommend_referral(
        symptoms_text=r.symptoms_text, category=p.category if p else "None",
        age=p.age if p else 0, vitals=vd, facilities=fl,
        capabilities_by_facility=cm, current_facility_type=r.facility_id or "PHC")
    decision = models.ReferralDecision(
        triage_case_id=r.id, priority=rec.priority,
        suggested_service=rec.suggested_service_code,
        suggested_facility_id=rec.suggested_facility_id,
        suggestion_reasons_json=json.dumps(
            rec.urgency_reasons + rec.service_reasons + rec.facility_reasons),
        routing_confidence=rec.routing_confidence)
    db.add(decision)
    db.commit()
    db.refresh(decision)
    return {"success": True, "decision_id": decision.id, "triage_id": r.id,
            "recommendation": rec.to_dict()}

@app.post("/api/referral/override/{decision_id}", tags=["referral"])
def override_referral(
    decision_id: int,
    new_service: str = Form(None),
    new_facility_id: int = Form(None),
    reason: str = Form(...),
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    d = db.query(models.ReferralDecision).filter(
        models.ReferralDecision.id == decision_id).first()
    if not d:
        raise HTTPException(404, "Decision not found")
    if d.priority == "P1" and new_service == "GEN_MED" and not reason.strip():
        raise HTTPException(400, "P1 cases cannot be downgraded without reason")
    orig = d.suggested_service
    ofid = d.suggested_facility_id
    d.final_service = new_service or d.suggested_service
    d.final_facility_id = new_facility_id or d.suggested_facility_id
    d.override_flag = True
    d.override_reason = reason
    d.finalized_at = _utcnow()
    db.add(models.AuditLog(user_id=user.id, record_id=d.triage_case_id,
                           action="REFERRAL_OVERRIDE",
                           details=f"Override: {orig}→{d.final_service}. Reason: {reason}"))
    db.commit()
    return {"success": True, "override": True,
            "original_service": orig, "final_service": d.final_service,
            "original_facility_id": ofid, "final_facility_id": d.final_facility_id,
            "overridden_by": user.username, "reason": reason}

# ═══════════════════════════════════════════════════════════
# FACILITIES
# ═══════════════════════════════════════════════════════════
@app.get("/api/facilities", tags=["facilities"])
def list_facilities(
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    return {"success": True, "facilities": [
        {"id": f.id, "code": f.facility_code, "name": f.facility_name,
         "type": f.facility_type, "district": f.district,
         "emergency_capable": f.emergency_capable,
         "operational_status": f.operational_status}
        for f in db.query(models.Facility).all()]}

@app.get("/api/facilities/{facility_id}/capabilities", tags=["facilities"])
def get_facility_capabilities(
    facility_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    caps = db.query(models.FacilityCapability).filter(
        models.FacilityCapability.facility_id == facility_id).all()
    return {"success": True, "capabilities": [
        {"service_code": c.service_code, "capability_level": c.capability_level,
         "availability_status": c.availability_status} for c in caps]}

# ═══════════════════════════════════════════════════════════
# ADMIN: DOCTOR ROSTER
# ═══════════════════════════════════════════════════════════
@app.get("/api/admin/doctors", tags=["admin"])
def list_doctors(
    db: Session = Depends(get_db),
    admin: models.User = Depends(require_admin),
):
    return {"success": True, "doctors": [{
        "id": d.id, "name": d.full_name, "username": d.username,
        "department": d.department, "facility_id": d.facility_id,
        "is_on_duty": d.is_on_duty, "current_load": d.current_load,
        "max_load": d.max_load, "years_experience": d.years_experience,
        "avg_consultation_mins": d.avg_consultation_mins,
        "total_assigned_today": d.total_assigned_today,
        "slots_available": max(0, d.max_load - d.current_load)}
        for d in db.query(models.User).filter(models.User.role == "doctor").all()]}

@app.patch("/api/admin/doctors/{doctor_id}/duty", tags=["admin"])
def toggle_doctor_duty(
    doctor_id: int,
    is_on_duty: bool = Form(...),
    db: Session = Depends(get_db),
    admin: models.User = Depends(require_admin),
):
    doc = db.query(models.User).filter(models.User.id == doctor_id).first()
    if not doc or doc.role != "doctor":
        raise HTTPException(404, "Doctor not found")
    doc.is_on_duty = is_on_duty
    db.add(models.AuditLog(user_id=admin.id, record_id=doc.id,
                           action="DOCTOR_DUTY_TOGGLE",
                           details=f"{doc.full_name} set to on_duty={is_on_duty}"))
    db.commit()
    return {"success": True, "doctor_id": doctor_id, "is_on_duty": is_on_duty}

@app.get("/api/admin/assignments", tags=["admin"])
def list_assignments(
    limit: int = 30,
    db: Session = Depends(get_db),
    admin: models.User = Depends(require_admin),
):
    rows = db.query(models.AssignmentDecision).order_by(
        models.AssignmentDecision.id.desc()).limit(limit).all()
    return {"success": True, "assignments": [{
        "id": r.id, "triage_record_id": r.triage_record_id,
        "chosen_doctor_id": r.chosen_doctor_id,
        "chosen_doctor_name": r.chosen_doctor_name,
        "chosen_doctor_department": r.chosen_doctor_department,
        "score": r.total_score,
        "candidates_considered": r.candidates_considered,
        "fallback_used": r.fallback_used,
        "reasons": _safe_json_loads(r.reasons_json, []),
        "candidate_scores": _safe_json_loads(r.candidate_scores_json, []),
        "at": r.created_at.isoformat() if r.created_at else None} for r in rows]}

# ═══════════════════════════════════════════════════════════
# DOCTORS: Available
# ═══════════════════════════════════════════════════════════
@app.get("/api/doctors/available", tags=["doctors"])
def available_doctors(
    department: Optional[str] = None,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    q = db.query(models.User).filter(
        models.User.role == "doctor", models.User.is_on_duty == True)  # noqa: E712
    if department:
        q = q.filter(models.User.department == department)
    docs = q.order_by(models.User.current_load.asc()).all()
    return {"success": True, "doctors": [{
        "id": d.id, "name": d.full_name, "department": d.department,
        "current_load": d.current_load, "max_load": d.max_load,
        "slots_available": max(0, d.max_load - d.current_load),
        "years_experience": d.years_experience,
        "avg_consultation_mins": d.avg_consultation_mins} for d in docs]}

# ═══════════════════════════════════════════════════════════
# EMR: HL7 FHIR
# ═══════════════════════════════════════════════════════════
@app.get("/api/emr/fhir/ServiceRequest/{record_id}", tags=["emr"])
def fhir_service_request(
    record_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    r = db.query(models.TriageRecord).filter(
        models.TriageRecord.id == record_id).first()
    if not r:
        raise HTTPException(404, "Record not found")
    p = db.query(models.Patient).filter(
        models.Patient.id == r.patient_id).first()
    doc = None
    if r.assigned_doctor_id:
        doc = db.query(models.User).filter(
            models.User.id == r.assigned_doctor_id).first()
    return {
        "resourceType": "ServiceRequest", "id": f"triage-{r.id}",
        "status": "active", "intent": "order",
        "priority": {"P1": "stat", "P2": "urgent", "P3": "asap", "P4": "routine"}.get(
            r.ai_priority, "routine"),
        "code": {"coding": [{"system": "http://snomed.info/sct",
                              "code": "11429006", "display": "Consultation"}],
                 "text": r.assigned_department or "General OPD"},
        "subject": {"reference": f"Patient/{p.id}" if p else None,
                    "display": p.name if p else "Unknown"},
        "reasonCode": [{"text": r.symptoms_text or "Not specified"}],
        "performer": [{"reference": f"Practitioner/{doc.id}" if doc else None,
                       "display": doc.full_name if doc else "Duty Medical Officer"}],
        "authoredOn": r.created_at.isoformat() if r.created_at else None,
        "note": [{"text": f"AI triage summary: {r.ai_summary or 'N/A'}"}]}

# ═══════════════════════════════════════════════════════════
# OPTIONAL ROUTERS
# ═══════════════════════════════════════════════════════════
if _EXTRA_ROUTERS_AVAILABLE:
    app.include_router(speech_router, prefix="/api", tags=["speech"])
    app.include_router(ocr_router, prefix="/api", tags=["ocr"])
    app.include_router(vision_router, prefix="/api", tags=["vision"])
else:
    logger.warning("Extra routers unavailable: %s", _extra_routers_import_error)