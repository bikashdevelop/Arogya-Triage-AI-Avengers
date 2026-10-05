from typing import Dict, Any, List, Optional
import re


# ==========================================================
# 1. PRIORITY CONSTANTS
# ==========================================================

PRIORITY_RANK = {"P1": 5, "P2": 4, "P3": 3, "P4": 2, "P5": 1}

PRIORITY_META = {
    "P1": {"color": "RED", "label": "IMMEDIATE / EMERGENCY", "target_time": "Immediate"},
    "P2": {"color": "ORANGE", "label": "VERY URGENT", "target_time": "Target clinical assessment within 10 minutes"},
    "P3": {"color": "YELLOW", "label": "URGENT", "target_time": "Target clinical assessment within 60 minutes"},
    "P4": {"color": "GREEN", "label": "STANDARD", "target_time": "Target clinical assessment within 120 minutes"},
    "P5": {"color": "BLUE", "label": "NON-URGENT", "target_time": "Target clinical assessment within 240 minutes"},
}


def priority_rank(priority: str) -> int:
    return PRIORITY_RANK.get(priority, 1)


def highest_priority(*priorities: str) -> str:
    valid = [p for p in priorities if p in PRIORITY_RANK]
    if not valid:
        return "P5"
    return max(valid, key=priority_rank)


def normalize_text(value: Any) -> str:
    if isinstance(value, list):
        value = " ".join(str(x) for x in value)
    text = str(value or "").lower()
    text = re.sub(r"\s+", " ", text).strip()
    return text


def safe_float(value: Any) -> Optional[float]:
    try:
        if value is None or str(value).strip() == "":
            return None
        return float(value)
    except (ValueError, TypeError):
        return None


def contains_any(text: str, terms: List[str]) -> List[str]:
    """
    Smart matching:
    1. Exact substring match
    2. Word-level match (for short forms like "bleeding" matching "vaginal bleeding")
    """
    matches = []
    text_lower = text.lower()
    
    # Critical clinical words
    critical_words = {
        "bleeding", "seizure", "convulsion", "unconscious",
        "headache", "vision", "movement", "breathing",
        "pain", "fever", "burn", "poisoning", "trauma",
        "distress", "shock", "paralysis", "weakness",
        "vomiting", "diarrhea", "dehydration", "injury",
    }
    
    text_words = set(re.findall(r'\b\w+\b', text_lower))
    
    for term in terms:
        # Exact match
        if term in text_lower:
            matches.append(term)
            continue
        
        # Word-level match
        term_words = set(re.findall(r'\b\w+\b', term.lower()))
        common_words = text_words & term_words
        
        # If any critical word matches, consider it a match
        if common_words & critical_words:
            matches.append(term)
    
    return matches


# ==========================================================
# 2. PATIENT GROUP
# ==========================================================

def get_age_group(age: int) -> str:
    if age < 1:
        return "infant"
    if age < 3:
        return "toddler"
    if age < 12:
        return "child"
    return "adult"


# ==========================================================
# 3. MTS SYMPTOM DISCRIMINATOR RULES
# ==========================================================

ADULT_P1_TERMS = [
    "not breathing", "unable to breathe", "severe respiratory distress",
    "gasping", "blue lips", "cyanosis", "choking",
    "unresponsive", "unconscious", "not waking up",
    "cardiac arrest", "crushing chest pain with sweating",
    "chest pain radiating to jaw with sweating", "severe chest pain with sweating",
    "seizure", "continuous seizure", "sudden one-sided weakness",
    "sudden weakness on one side", "face drooping", "slurred speech",
    "speech difficulty", "stroke symptoms", "paralysis",
    "shock", "active massive bleeding", "uncontrolled heavy bleeding",
    "vomiting large amounts of blood", "coughing up blood",
    "anaphylaxis", "severe allergic reaction", "swelling of throat",
    "poisoning", "overdose", "snake bite", "scorpion sting", "dog bite",
    "major burn", "severe burn", "chemical burn", "acid burn",
    "fire burn", "flame burn", "electrical burn", "scald",
    "burn on face", "burn on neck", "burn on chest", "burn on hands",
    "burn on genital", "burn covering large area",
    "major trauma", "head injury with unconsciousness",
    "severe accident", "severe fall",
]

ADULT_P2_TERMS = [
    "chest pain", "shortness of breath", "moderate breathing difficulty",
    "fainting", "persistent vomiting", "vomiting blood",
    "black stool", "black stools", "severe abdominal pain",
    "severe headache", "high fever with confusion",
    "moderate bleeding", "severe dehydration", "sudden severe back pain",
    "burn", "burning", "burn on arm", "burn on leg",
    "burn on back", "minor burn", "superficial burn",
    "fracture", "broken bone", "deep cut", "wound",
    "ingested poison", "swallowed chemical",
]

ADULT_P3_TERMS = [
    "fever", "vomiting", "diarrhea", "moderate abdominal pain",
    "moderate headache", "painful urination", "cough with fever",
    "dizziness", "rash", "sore throat", "ear pain",
    "minor cut", "bruise", "sprain",
]

PEDIATRIC_P1_TERMS = [
    "not breathing", "blue lips", "cyanosis", "unresponsive", "unconscious",
    "convulsion", "convulsions", "seizure", "seizures",
    "severe respiratory distress", "chest indrawing", "shock",
    "bulging fontanelle", "stiff neck with altered consciousness",
    "severe dehydration with lethargy",
    "severe burn", "scald", "poisoning", "snake bite",
]

PEDIATRIC_P2_TERMS = [
    "difficulty breathing", "breathing fast", "persistent vomiting",
    "unable to feed", "refusing to feed", "poor feeding", "lethargy",
    "sunken eyes", "no urine", "not passing urine", "high fever",
    "stiff neck", "severe diarrhea",
    "burn", "burning", "minor burn",
]

PEDIATRIC_P3_TERMS = [
    "fever", "cough", "vomiting", "diarrhea", "rash",
    "ear pain", "sore throat", "minor cut",
]

PREGNANCY_P1_TERMS = [
    # Long forms
    "heavy vaginal bleeding",
    "vaginal bleeding with dizziness",
    "severe abdominal pain",
    "severe headache with blurred vision",
    "severe headache with vision changes",
    "convulsion", "seizure", "unconscious",
    "difficulty breathing", "chest pain",
    "no fetal movement",
    "reduced fetal movement with pain",
    "eclampsia",
    "severe swelling with headache",
    "severe burn", "poisoning", "major trauma",
    # Short forms
    "severe bleeding",
    "vaginal bleeding",
    "bleeding",
    "heavy bleeding",
    "severe headache",
    "blurred vision",
    "vision changes",
    "reduced fetal movement",
    "severe swelling",
]

PREGNANCY_P2_TERMS = [
    "spotting",
    "headache",
    "swelling of face",
    "swelling of hands",
    "persistent vomiting",
    "fever",
    "painful urination",
    "fluid leakage",
    "abdominal pain",
    "burn",
    "burning",
]


def get_mts_symptom_priority(symptoms: List[str], age: int, pregnant: bool) -> Dict[str, Any]:
    symptoms_text = normalize_text(symptoms)
    age_group = get_age_group(age)

    p1_terms = list(ADULT_P1_TERMS)
    p2_terms = list(ADULT_P2_TERMS)
    p3_terms = list(ADULT_P3_TERMS)

    if age_group in ["infant", "toddler", "child"]:
        p1_terms.extend(PEDIATRIC_P1_TERMS)
        p2_terms.extend(PEDIATRIC_P2_TERMS)
        p3_terms.extend(PEDIATRIC_P3_TERMS)

    if pregnant:
        p1_terms.extend(PREGNANCY_P1_TERMS)
        p2_terms.extend(PREGNANCY_P2_TERMS)

    p1_matches = contains_any(symptoms_text, p1_terms)
    p2_matches = contains_any(symptoms_text, p2_terms)
    p3_matches = contains_any(symptoms_text, p3_terms)

    if p1_matches:
        return {"priority": "P1", "reason": "Immediate symptom-based danger discriminator detected.", "matched_discriminators": p1_matches}
    if p2_matches:
        return {"priority": "P2", "reason": "Very urgent symptom-based discriminator detected.", "matched_discriminators": p2_matches}
    if p3_matches:
        return {"priority": "P3", "reason": "Urgent symptom-based discriminator detected.", "matched_discriminators": p3_matches}

    return {"priority": "P4", "reason": "No configured high-risk symptom discriminator identified; clinician assessment still required.", "matched_discriminators": []}


# ==========================================================
# 4. IMMEDIATE VITAL-SIGN RED FLAGS
# ==========================================================

def get_vital_red_flags(vitals: Dict[str, Any], age: int, pregnant: bool) -> List[str]:
    flags = []
    age_group = get_age_group(age)

    spo2 = safe_float(vitals.get("spo2"))
    rr = safe_float(vitals.get("respiratory_rate"))
    hr = safe_float(vitals.get("heart_rate"))
    sbp = safe_float(vitals.get("systolic_bp"))
    consciousness = normalize_text(vitals.get("consciousness"))

    if consciousness in ["unresponsive", "unconscious", "voice", "pain"]:
        flags.append("Altered consciousness / reduced responsiveness reported")

    if spo2 is not None and spo2 < 90:
        flags.append(f"SpO₂ critically low: {spo2}%")

    if age_group == "adult":
        if rr is not None:
            if rr >= 30:
                flags.append(f"Respiratory rate critically high: {rr}/min")
            if rr < 8:
                flags.append(f"Respiratory rate critically low: {rr}/min")
        if sbp is not None and sbp < 90:
            flags.append(f"Systolic BP critically low: {sbp} mmHg")
        if hr is not None:
            if hr >= 140:
                flags.append(f"Heart rate critically high: {hr}/min")
            if hr < 40:
                flags.append(f"Heart rate critically low: {hr}/min")

    if pregnant:
        if sbp is not None:
            if sbp >= 160:
                flags.append(f"Severely high pregnancy BP: {sbp} mmHg")
            if sbp < 90:
                flags.append(f"Low pregnancy BP: {sbp} mmHg")

    return flags


# ==========================================================
# 5. MEWS CALCULATOR
# ==========================================================

def calculate_mews(vitals: Dict[str, Any], age: int = 30, pregnant: bool = False) -> Dict[str, Any]:
    score = 0
    breakdown = []
    age_group = get_age_group(age)

    rr = safe_float(vitals.get("respiratory_rate"))
    hr = safe_float(vitals.get("heart_rate"))
    sbp = safe_float(vitals.get("systolic_bp"))
    spo2 = safe_float(vitals.get("spo2"))
    consciousness = normalize_text(vitals.get("consciousness"))

    temp = None
    temp_f = safe_float(vitals.get("temperature_f"))
    temp_c = safe_float(vitals.get("temperature_c"))
    if temp_f is not None:
        temp = (temp_f - 32) * 5 / 9
    elif temp_c is not None:
        temp = temp_c

    if rr is not None:
        if rr < 9:
            score += 2
            breakdown.append("RR < 9 (+2)")
        elif 21 <= rr <= 29:
            score += 2
            breakdown.append("RR 21-29 (+2)")
        elif rr >= 30:
            score += 3
            breakdown.append("RR >= 30 (+3)")

    if hr is not None:
        if hr < 40:
            score += 2
            breakdown.append("HR < 40 (+2)")
        elif 41 <= hr <= 50:
            score += 1
            breakdown.append("HR 41-50 (+1)")
        elif 101 <= hr <= 110:
            score += 1
            breakdown.append("HR 101-110 (+1)")
        elif 111 <= hr <= 129:
            score += 2
            breakdown.append("HR 111-129 (+2)")
        elif hr >= 130:
            score += 3
            breakdown.append("HR >= 130 (+3)")

    if sbp is not None:
        if sbp < 70:
            score += 3
            breakdown.append("SBP < 70 (+3)")
        elif 70 <= sbp <= 80:
            score += 2
            breakdown.append("SBP 70-80 (+2)")
        elif 81 <= sbp <= 100:
            score += 1
            breakdown.append("SBP 81-100 (+1)")
        elif sbp > 200:
            score += 2
            breakdown.append("SBP > 200 (+2)")

    if temp is not None:
        if temp < 35:
            score += 2
            breakdown.append("Temperature < 35C (+2)")
        elif temp > 38.4:
            score += 2
            breakdown.append("Temperature > 38.4C (+2)")

    if spo2 is not None:
        if spo2 < 90:
            score += 3
            breakdown.append("SpO2 < 90% (+3)")
        elif 90 <= spo2 <= 93:
            score += 2
            breakdown.append("SpO2 90-93% (+2)")
        elif 94 <= spo2 <= 95:
            score += 1
            breakdown.append("SpO2 94-95% (+1)")

    if consciousness in ["voice", "pain", "unresponsive", "unconscious", "confused"]:
        score += 3
        breakdown.append("Altered consciousness / confusion (+3)")

    if pregnant:
        patient_type = "pregnant"
    elif age_group != "adult":
        patient_type = "pediatric"
    else:
        patient_type = "adult"

    return {"score": score, "breakdown": breakdown, "age_group": age_group, "patient_type": patient_type}


def mews_escalation_only(mews_score: int) -> Dict[str, str]:
    if mews_score >= 5:
        return {"priority": "P1", "reason": "High MEWS: severe physiological deterioration signal."}
    if mews_score >= 3:
        return {"priority": "P2", "reason": "Moderate MEWS: urgent physiological deterioration signal."}
    if mews_score >= 1:
        return {"priority": "P3", "reason": "Abnormal MEWS: enhanced observation / clinician review required."}
    return {"priority": "P4", "reason": "MEWS does not require escalation at this time."}


# ==========================================================
# 6. LAB / OCR INTERPRETATION
# ==========================================================

def interpret_lab_findings(lab_findings: Dict[str, Any]) -> Dict[str, Any]:
    if not lab_findings:
        return {"critical_alerts": [], "urgent_alerts": [], "interpretations": [], "recommended_escalation": "P4", "verification_required": False}

    critical_alerts = []
    urgent_alerts = []
    interpretations = []

    hb = safe_float(lab_findings.get("hemoglobin", lab_findings.get("hb")))
    if hb is not None:
        if hb < 7:
            critical_alerts.append(f"Reported hemoglobin {hb} g/dL: critical value; verify and urgently review.")
        elif hb < 10:
            urgent_alerts.append(f"Reported hemoglobin {hb} g/dL: low value; clinician review required.")
        else:
            interpretations.append(f"Reported hemoglobin: {hb} g/dL")

    platelets = safe_float(lab_findings.get("platelets", lab_findings.get("plt")))
    if platelets is not None:
        if platelets < 50000:
            critical_alerts.append(f"Reported platelets {platelets}: critical low result; verify and urgently review.")
        elif platelets < 100000:
            urgent_alerts.append(f"Reported platelets {platelets}: low result; clinician review required.")
        else:
            interpretations.append(f"Reported platelets: {platelets}")

    glucose = safe_float(lab_findings.get("blood_sugar", lab_findings.get("glucose")))
    if glucose is not None:
        if glucose < 54:
            critical_alerts.append(f"Reported glucose {glucose} mg/dL: critical low result; verify and urgently review.")
        elif glucose < 70:
            urgent_alerts.append(f"Reported glucose {glucose} mg/dL: low result; clinician review required.")
        elif glucose > 300:
            urgent_alerts.append(f"Reported glucose {glucose} mg/dL: markedly high result; assess clinically.")
        else:
            interpretations.append(f"Reported glucose: {glucose} mg/dL")

    creatinine = safe_float(lab_findings.get("creatinine"))
    if creatinine is not None:
        if creatinine > 3:
            urgent_alerts.append(f"Reported creatinine {creatinine} mg/dL: markedly high; clinician review required.")
        else:
            interpretations.append(f"Reported creatinine: {creatinine} mg/dL")

    troponin = safe_float(lab_findings.get("troponin"))
    if troponin is not None:
        urgent_alerts.append("Troponin value reported: interpret only with assay-specific reference range, ECG, symptoms, and clinician review.")

    if critical_alerts:
        escalation = "P2"
    elif urgent_alerts:
        escalation = "P3"
    else:
        escalation = "P4"

    return {"critical_alerts": critical_alerts, "urgent_alerts": urgent_alerts, "interpretations": interpretations, "recommended_escalation": escalation, "verification_required": bool(critical_alerts or urgent_alerts)}


# ==========================================================
# 7. FACILITY ROUTING
# ==========================================================

def get_routing(priority: str, age: int, pregnant: bool, facility: str) -> Dict[str, Any]:
    age_group = get_age_group(age)
    facility_text = normalize_text(facility)
    is_primary_facility = any(term in facility_text for term in ["phc", "primary", "sub centre", "sub-center", "health camp"])

    if priority == "P1":
        if pregnant:
            department = "Obstetric Emergency / Labour Room"
            referral = "Arrange emergency transfer to a higher facility with OB/GYN, blood-bank and newborn-care capability if unavailable locally."
        elif age_group != "adult":
            department = "Pediatric Emergency / Resuscitation"
            referral = "Arrange emergency pediatric referral if advanced emergency care is unavailable locally."
        else:
            department = "Emergency Resuscitation Bay"
            referral = "Arrange emergency inter-facility transfer if resuscitation/critical-care services are unavailable locally."

        return {"recommended_department": department, "referral_advice": referral if is_primary_facility else None, "checklist": ["Immediately alert trained clinical staff.", "Start facility-approved emergency protocol.", "Repeat and manually verify critical vital signs.", "Document symptom onset, key findings, and time of escalation.", "Do not delay emergency care for additional AI questioning."]}

    if priority == "P2":
        if pregnant:
            department = "OB/GYN Urgent Assessment"
        elif age_group != "adult":
            department = "Pediatric Urgent Assessment"
        else:
            department = "Emergency / Urgent Clinical Assessment"

        return {"recommended_department": department, "referral_advice": "Consider referral according to local capability and clinician assessment." if is_primary_facility else None, "checklist": ["Prioritize for clinician assessment.", "Repeat abnormal vital signs.", "Confirm extracted/OCR values before acting on them.", "Re-triage immediately if symptoms worsen."]}

    if priority == "P3":
        return {"recommended_department": "Urgent OPD / Clinical Assessment Area", "referral_advice": None, "checklist": ["Obtain missing relevant history and repeat vital signs.", "Ensure clinician assessment within the local target time.", "Re-triage if condition worsens while waiting."]}

    return {"recommended_department": "General OPD / Primary Care Assessment", "referral_advice": None, "checklist": ["Complete clinical assessment by qualified health worker.", "Provide facility-approved safety-net instructions.", "Re-triage immediately if symptoms worsen or new danger signs appear."]}


# ==========================================================
# 8. MISSING INFORMATION AND FOLLOW-UP QUESTIONS
# ==========================================================

def get_missing_information(patient_data: Dict[str, Any], age: int, pregnant: bool) -> List[str]:
    vitals = patient_data.get("vitals", {})
    symptoms_text = normalize_text(patient_data.get("symptoms", []))
    missing = []

    if not symptoms_text: missing.append("Chief complaint and symptom onset")
    if safe_float(vitals.get("respiratory_rate")) is None: missing.append("Respiratory rate")
    if safe_float(vitals.get("heart_rate")) is None: missing.append("Heart rate / pulse")
    if safe_float(vitals.get("systolic_bp")) is None: missing.append("Systolic blood pressure")
    if safe_float(vitals.get("spo2")) is None: missing.append("Oxygen saturation (SpO2), if a pulse oximeter is available")
    if "onset" not in symptoms_text and "since" not in symptoms_text: missing.append("Time of symptom onset")

    if pregnant:
        if "week" not in symptoms_text and "trimester" not in symptoms_text: missing.append("Gestational age / trimester")
        if "fetal movement" not in symptoms_text: missing.append("Fetal movement status")
        if "bleeding" not in symptoms_text: missing.append("Presence or absence of vaginal bleeding")
        if "fluid" not in symptoms_text and "water" not in symptoms_text: missing.append("Fluid leakage / rupture of membranes status")

    if age < 12:
        if "feed" not in symptoms_text: missing.append("Feeding status")
        if "urine" not in symptoms_text: missing.append("Urine output / wet diapers")
        if "immun" not in symptoms_text: missing.append("Immunization status, if relevant")

    return missing


def get_follow_up_questions(age: int, pregnant: bool, priority: str) -> List[str]:
    emergency_questions = [
        "Can the patient speak in full sentences?",
        "Is the patient awake and responding normally?",
        "Is there severe bleeding, seizure, fainting, or sudden weakness on one side?",
        "What are the latest blood pressure, pulse, respiratory rate, temperature, and SpO2?",
    ]

    if priority == "P1":
        return ["Emergency signs detected: alert a trained health worker now.", "When did the symptoms begin?", "Is the patient conscious and breathing normally?", "Please confirm the latest vital signs if this does not delay care."]

    if pregnant:
        return emergency_questions + ["How many weeks pregnant are you?", "Is the baby moving normally, reduced, or not moving?", "Is there bleeding, fluid leakage, severe headache, blurred vision, or severe abdominal pain?"]

    if age < 12:
        return emergency_questions + ["Is the child feeding normally?", "Has urine output reduced?", "Is there chest indrawing, fast breathing, rash, or convulsion?"]

    return emergency_questions + ["When did the symptoms start, and are they getting worse?", "Is there chest pain, severe headache, persistent vomiting, or confusion?", "Does the patient have diabetes, heart disease, asthma, kidney disease, or recent surgery?"]


# ==========================================================
# 9. FINAL TRIAGE DECISION
# ==========================================================

def determine_triage(symptoms: List[str], vitals: Dict[str, Any], age: int, pregnant: bool, facility: str, lab_findings: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    mts_result = get_mts_symptom_priority(symptoms, age, pregnant)
    vital_red_flags = get_vital_red_flags(vitals, age, pregnant)
    mews_result = calculate_mews(vitals, age, pregnant)
    mews_result["escalation"] = mews_escalation_only(mews_result["score"])
    lab_result = interpret_lab_findings(lab_findings or {})

    if vital_red_flags:
        immediate_vital_priority = "P1"
    else:
        immediate_vital_priority = "P5"

    final_priority = highest_priority(mts_result["priority"], immediate_vital_priority, mews_result["escalation"]["priority"], lab_result["recommended_escalation"])

    decision_reasons = []
    decision_reasons.append(f"MTS symptom baseline: {mts_result['priority']} — {mts_result['reason']}")

    if mts_result["matched_discriminators"]:
        decision_reasons.append("Matched symptom discriminators: " + ", ".join(mts_result["matched_discriminators"]))

    if vital_red_flags:
        decision_reasons.append("Immediate vital-sign safety override: " + "; ".join(vital_red_flags))

    mews_rank = priority_rank(mews_result["escalation"]["priority"])
    mts_rank = priority_rank(mts_result["priority"])
    if mews_rank > mts_rank:
        decision_reasons.append(f"Escalated by MEWS {mews_result['score']} to {mews_result['escalation']['priority']}: {mews_result['escalation']['reason']}")
    else:
        decision_reasons.append(f"MEWS {mews_result['score']} did not downgrade the symptom-based MTS priority.")

    if lab_result["recommended_escalation"] != "P4":
        decision_reasons.append(f"Lab/OCR escalation candidate: {lab_result['recommended_escalation']} (requires manual verification).")

    if lab_result["critical_alerts"]:
        decision_reasons.append("Critical reported lab alerts: " + "; ".join(lab_result["critical_alerts"]))

    routing = get_routing(final_priority, age, pregnant, facility)

    return {"priority": final_priority, "priority_meta": PRIORITY_META[final_priority], "decision_reasons": decision_reasons, "mts_result": mts_result, "vital_red_flags": vital_red_flags, "mews_result": mews_result, "lab_result": lab_result, "routing": routing, "human_review_required": True}


# ==========================================================
# 10. MAIN ORCHESTRATOR
# ==========================================================

def run_triage_assessment(patient_data: Dict[str, Any]) -> Dict[str, Any]:
    demographics = patient_data.get("demographics", {})
    vitals = patient_data.get("vitals", {})
    symptoms = patient_data.get("symptoms", [])
    lab_findings = patient_data.get("lab_findings", {})
    facility = patient_data.get("facility", "Primary Health Centre (PHC)")
    patient_category = normalize_text(patient_data.get("patient_category", ""))

    age_value = demographics.get("age", 30)
    age = int(safe_float(age_value) or 30)

    pregnant = patient_category == "pregnancy"

    triage = determine_triage(symptoms=symptoms, vitals=vitals, age=age, pregnant=pregnant, facility=facility, lab_findings=lab_findings)

    missing_info = get_missing_information(patient_data=patient_data, age=age, pregnant=pregnant)
    questions = get_follow_up_questions(age=age, pregnant=pregnant, priority=triage["priority"])

    return {
        "status": "success",
        "provisional_triage": {"priority_code": triage["priority"], "color": triage["priority_meta"]["color"], "label": triage["priority_meta"]["label"], "target_assessment_time": triage["priority_meta"]["target_time"], "human_review_required": triage["human_review_required"]},
        "triage_reasoning": triage["decision_reasons"],
        "symptom_mts_baseline": {"priority": triage["mts_result"]["priority"], "reason": triage["mts_result"]["reason"], "matched_discriminators": triage["mts_result"]["matched_discriminators"]},
        "physiological_deterioration": {"mews_score": triage["mews_result"]["score"], "mews_breakdown": triage["mews_result"]["breakdown"], "mews_escalation": triage["mews_result"]["escalation"], "immediate_vital_red_flags": triage["vital_red_flags"]},
        "lab_ocr_review": {"critical_alerts": triage["lab_result"]["critical_alerts"], "urgent_alerts": triage["lab_result"]["urgent_alerts"], "interpretations": triage["lab_result"]["interpretations"], "verification_required": triage["lab_result"]["verification_required"]},
        "routing": triage["routing"],
        "identified_missing_info": missing_info,
        "prioritized_questions": questions,
        "disclaimer": "Educational triage-support prototype only. This output is not a diagnosis, prescription, or discharge decision. A qualified healthcare professional must review, confirm, modify, or override every triage result. For severe symptoms, seek emergency care immediately.",
    }
