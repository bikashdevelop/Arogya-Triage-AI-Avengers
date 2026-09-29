from typing import Dict, Any, List

# 1. MEWS CALCULATOR
 

def calculate_mews(vitals: Dict[str, Any]) -> Dict[str, Any]:
    score = 0
    breakdown = []
    
    rr = vitals.get('respiratory_rate', 16)
    if rr < 9: score += 2; breakdown.append("RR < 9 (+2)")
    elif 15 <= rr <= 20: score += 1; breakdown.append("RR 15-20 (+1)")
    elif 21 <= rr <= 29: score += 2; breakdown.append("RR 21-29 (+2)")
    elif rr >= 30: score += 3; breakdown.append("RR >= 30 (+3)")

    hr = vitals.get('heart_rate', 80)
    if hr < 40: score += 2; breakdown.append("HR < 40 (+2)")
    elif 41 <= hr <= 50: score += 1; breakdown.append("HR 41-50 (+1)")
    elif 101 <= hr <= 110: score += 1; breakdown.append("HR 101-110 (+1)")
    elif 111 <= hr <= 129: score += 2; breakdown.append("HR 111-129 (+2)")
    elif hr >= 130: score += 3; breakdown.append("HR >= 130 (+3)")
    
    bp = vitals.get('systolic_bp', 120)
    if bp < 70: score += 3; breakdown.append("SBP < 70 (+3)")
    elif 71 <= bp <= 80: score += 2; breakdown.append("SBP 71-80 (+2)")
    elif 81 <= bp <= 100: score += 1; breakdown.append("SBP 81-100 (+1)")
    elif bp > 200: score += 2; breakdown.append("SBP > 200 (+2)")
    
    temp_f = vitals.get('temperature_f', 98.6)
    temp_c = (temp_f - 32) * 5/9 if temp_f > 45 else temp_f
    if temp_c < 35: score += 2; breakdown.append("Temp < 35C (+2)")
    elif temp_c > 38.4: score += 2; breakdown.append(f"Temp > 38.4C ({temp_f}F) (+2)")
    
    spo2 = vitals.get('spo2', 98)
    if spo2 < 90: score += 3; breakdown.append("SpO2 < 90% (+3)")
    elif 90 <= spo2 <= 93: score += 2; breakdown.append("SpO2 90-93% (+2)")
    elif 94 <= spo2 <= 95: score += 1; breakdown.append("SpO2 94-95% (+1)")

    return {"score": score, "breakdown": breakdown}



# 2. MANCHESTER TRIAGE & ROUTING

def determine_triage(symptoms: List[str], mews_score: int, facility: str) -> Dict[str, Any]:
    symptoms_str = " ".join(symptoms).lower()
    
    p1_flags = ["crushing chest pain", "radiating to jaw", "diaphoresis", "severe respiratory distress", "unresponsive", "shock", "blurring of vision", "severe frontal headache", "pregnancy"]
    p2_flags = ["uncontrolled diabetes", "diabetic foot sore", "severe chronic anemia", "tachycardia", "high fever", "severe dehydration"]

    priority = "P4"
    reason = "Routine vitals, stable presentation."
    dept = "General Outpatient (OPD)"
    referral = None
    checklist = []
    
    if mews_score >= 5 or any(flag in symptoms_str for flag in p1_flags):
        priority = "P1"
        reason = "Critical emergency. Immediate intervention required."
        dept = "Emergency Resuscitation Bay / ICU"
        checklist = ["Proceed with standard vitals monitoring", "Keep patient hydrated and monitor vitals every 15 mins", "Prepare ABHA digital health record"]
        if "PHC" in facility or "Primary" in facility:
            referral = "INTER-FACILITY REFERRAL RECOMMENDED: Transfer to District Hospital (DH) or CHC."
    elif mews_score >= 3 or any(flag in symptoms_str for flag in p2_flags):
        priority = "P2"
        reason = "Urgent condition requiring prompt review."
        dept = "Urgent Care / Specialist OPD"
        checklist = ["Monitor vitals every 30 minutes", "Prepare for specialist consultation"]
    elif mews_score >= 1:
        priority = "P3"
        reason = "Semi-urgent. Requires attention within 30-60 mins."
        dept = "General Outpatient (OPD)"
        checklist = ["Provide symptomatic relief", "Schedule follow-up in 24-48 hours"]

    if "pregnancy" in symptoms_str or "maternal" in symptoms_str:
        dept = "Obstetrics & Gynecology (OB/GYN)"
    elif "chemical fume" in symptoms_str or "inhalation" in symptoms_str:
        dept = "Pulmonology / Toxicology"

    return {
        "priority_level": priority,
        "priority_label": f"{priority} {'EMERGENCY' if priority=='P1' else 'URGENT' if priority=='P2' else 'SEMI-URGENT' if priority=='P3' else 'ROUTINE'}",
        "triage_reason": reason,
        "recommended_department": dept,
        "referral_advice": referral,
        "immediate_checklist": checklist
    }

# STRUCTURED SUMMARY GENERATOR


def generate_structured_summary(patient_data: Dict[str, Any], mews_score: int, triage_result: Dict[str, Any]) -> List[Dict[str, str]]:
    summary = []
    
    demographics = patient_data.get("demographics", {})
    symptoms = patient_data.get("symptoms", [])
    lab_findings = patient_data.get("lab_findings", {})
    vitals = patient_data.get("vitals", {})
    
    # 1. Demographics
    age = demographics.get("age")
    gender = demographics.get("gender")
    if age and gender:
        summary.append({"info": f"{age}y {gender}", "source": "Patient Demographics"})
    
    # 2. Symptoms
    for symptom in symptoms:
        summary.append({"info": symptom, "source": "Nurse Input (Text/Voice)"})
    
    # 3. Vitals with Interpretation
    if vitals:
        # --- BP Interpret ---
        bp = vitals.get('systolic_bp', 0)
        if bp >= 180:
            bp_status = "VERY HIGH ↑↑"
        elif bp >= 140:
            bp_status = "HIGH ↑"
        elif bp >= 90:
            bp_status = "NORMAL"
        elif bp >= 70:
            bp_status = "LOW ↓"
        else:
            bp_status = "VERY LOW ↓↓"
        
        # --- HR Interpret ---
        hr = vitals.get('heart_rate', 0)
        if hr >= 130:
            hr_status = "VERY HIGH ↑↑"
        elif hr >= 100:
            hr_status = "HIGH ↑"
        elif hr >= 60:
            hr_status = "NORMAL"
        elif hr >= 40:
            hr_status = "LOW ↓"
        else:
            hr_status = "VERY LOW ↓↓"
        
        # --- SpO2 Interpret ---
        spo2 = vitals.get('spo2', 100)
        if spo2 < 90:
            spo2_status = "CRITICAL ↓↓"
        elif spo2 < 95:
            spo2_status = "LOW ↓"
        else:
            spo2_status = "NORMAL"
        
        # --- Temperature Interpret ---
        temp = vitals.get('temperature_f', 98.6)
        if temp >= 103:
            temp_status = "VERY HIGH ↑↑"
        elif temp >= 100.4:
            temp_status = "HIGH ↑ (Fever)"
        elif temp >= 97:
            temp_status = "NORMAL"
        else:
            temp_status = "LOW ↓"
        
        # --- Combined Vitals Summary ---
        vitals_text = (
            f"BP {vitals.get('systolic_bp', '?')}/{vitals.get('diastolic_bp', '?')} ({bp_status}) | "
            f"HR {vitals.get('heart_rate', '?')} bpm ({hr_status}) | "
            f"SpO2 {vitals.get('spo2', '?')}% ({spo2_status}) | "
            f"Temp {vitals.get('temperature_f', '?')}°F ({temp_status})"
        )
        
        summary.append({"info": vitals_text, "source": "Vitals (Nurse Form)"})
    
    # 4. Lab Findings (OCR)
    if lab_findings:
        for key, value in lab_findings.items():
            summary.append({"info": f"{key.capitalize()}: {value}", "source": "OCR Lab Report"})
    
    # 5. MEWS Score
    summary.append({"info": f"MEWS Score: {mews_score}", "source": "Vitals Calculation"})
    
    # 6. Triage Priority
    summary.append({"info": f"Priority: {triage_result.get('priority_label', 'N/A')}", "source": "Manchester Triage Engine"})
    
    # 7. Routing
    summary.append({"info": f"Routing: {triage_result.get('recommended_department', 'N/A')}", "source": "Routing Engine"})
    
    # 8. Referral
    if triage_result.get('referral_advice'):
        summary.append({"info": triage_result['referral_advice'][:60] + "...", "source": "Referral Logic"})
    
    return summary


# 3. MAIN ORCHESTRATOR

def run_triage_assessment(patient_data: Dict[str, Any]) -> Dict[str, Any]:
    vitals = patient_data.get("vitals", {})
    symptoms = patient_data.get("symptoms", [])
    facility = patient_data.get("facility", "Primary Health Centre (PHC)")
    
    mews_result = calculate_mews(vitals)
    triage_result = determine_triage(symptoms, mews_result["score"], facility)
    
    missing_info = []
    symptoms_str = " ".join(symptoms).lower()
    if "cabg" not in symptoms_str:
        missing_info.append("Prior history of cardiac interventions / CABG")
    if "aspirin" not in symptoms_str and "meal" not in symptoms_str:
        missing_info.append("Time of last meal / aspirin intake")
        
    questions = [
        "Have you noticed any dizziness, blurred vision, or fainting?",
        "Can you keep fluids down, or is there persistent nausea/vomiting?",
        "Are there any other family or work members experiencing identical symptoms?"
    ]
    
    # Structured Summary
    structured_summary = generate_structured_summary(patient_data, mews_result["score"], triage_result)
    
    return {
        "status": "success",
        "mews_score": mews_result["score"],
        "mews_breakdown": mews_result["breakdown"],
        "triage_priority": triage_result["priority_label"],
        "triage_reason": triage_result["triage_reason"],
        "structured_summary": structured_summary,
        "routing": {
            "recommended_department": triage_result["recommended_department"],
            "referral_advice": triage_result["referral_advice"],
            "immediate_checklist": triage_result["immediate_checklist"]
        },
        "identified_missing_info": missing_info,
        "prioritized_questions": questions,
        "disclaimer": "STATUTORY NON-DIAGNOSTIC HEALTHCARE ADVISORY NOTICE: CLINICAL ADVISORY ONLY."
    }