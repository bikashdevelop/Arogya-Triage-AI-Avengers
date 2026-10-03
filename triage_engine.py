from typing import Dict, Any, List


# ==========================================
# 0. AGE GROUP DETECTION
# ==========================================
def get_age_group(age: int) -> str:
    """Age ke hisaab se group - pediatric ranges ke liye"""
    if age < 1: return "infant"
    elif age < 3: return "toddler"
    elif age < 12: return "child"
    else: return "adult"


# ==========================================
# 0.5. LAB FINDINGS INTERPRETER (OCR Data)
# ==========================================
def interpret_lab_findings(lab_findings: Dict[str, Any]) -> Dict[str, Any]:
    """
    OCR se aaye lab values ko interpret karo aur red flags return karo.
    """
    if not lab_findings:
        return {"red_flags": [], "bonus_score": 0, "interpretations": []}
    
    red_flags = []
    bonus_score = 0
    interpretations = []
    
    # === Hemoglobin (Anemia Detection) ===
    hb = lab_findings.get("hemoglobin") or lab_findings.get("hb")
    if hb:
        try:
            hb = float(hb)
            if hb < 7:
                red_flags.append("SEVERE ANEMIA detected")
                bonus_score += 3
                interpretations.append(f"Hemoglobin {hb} g/dL — CRITICAL LOW")
            elif hb < 10:
                bonus_score += 1
                interpretations.append(f"Hemoglobin {hb} g/dL — LOW")
            else:
                interpretations.append(f"Hemoglobin {hb} g/dL — NORMAL")
        except: pass
    
    # === Platelets (Bleeding Risk) ===
    plt = lab_findings.get("platelets") or lab_findings.get("plt")
    if plt:
        try:
            plt = float(plt)
            if plt < 50000:
                red_flags.append("SEVERE THROMBOCYTOPENIA — Bleeding risk")
                bonus_score += 3
                interpretations.append(f"Platelets {plt} — CRITICAL LOW")
            elif plt < 100000:
                bonus_score += 1
                interpretations.append(f"Platelets {plt} — LOW")
        except: pass
    
    # === WBC (Infection/Sepsis) ===
    wbc = lab_findings.get("wbc")
    if wbc:
        try:
            wbc = float(wbc)
            if wbc > 15000:
                red_flags.append("Possible SEPSIS — High WBC")
                bonus_score += 2
                interpretations.append(f"WBC {wbc} — HIGH (infection)")
            elif wbc > 11000:
                bonus_score += 1
                interpretations.append(f"WBC {wbc} — Slightly HIGH")
        except: pass
    
    # === Blood Sugar (Diabetes) ===
    sugar = lab_findings.get("blood_sugar") or lab_findings.get("glucose")
    if sugar:
        try:
            sugar = float(sugar)
            if sugar > 300:
                red_flags.append("SEVERE HYPERGLYCEMIA — Diabetic emergency")
                bonus_score += 2
                interpretations.append(f"Blood Sugar {sugar} mg/dL — CRITICAL HIGH")
            elif sugar > 180:
                bonus_score += 1
                interpretations.append(f"Blood Sugar {sugar} mg/dL — HIGH")
            elif sugar < 70:
                red_flags.append("HYPOGLYCEMIA — Low sugar emergency")
                bonus_score += 2
                interpretations.append(f"Blood Sugar {sugar} mg/dL — LOW")
        except: pass
    
    # === Creatinine (Kidney Function) ===
    creat = lab_findings.get("creatinine")
    if creat:
        try:
            creat = float(creat)
            if creat > 3:
                red_flags.append("KIDNEY FAILURE — High creatinine")
                bonus_score += 2
                interpretations.append(f"Creatinine {creat} mg/dL — CRITICAL HIGH")
        except: pass
    
    # === Troponin (Heart Attack) ===
    troponin = lab_findings.get("troponin")
    if troponin:
        try:
            troponin = float(troponin)
            if troponin > 0.04:
                red_flags.append("HEART ATTACK — High Troponin")
                bonus_score += 3
                interpretations.append(f"Troponin {troponin} — HIGH (cardiac event)")
        except: pass
    
    return {
        "red_flags": red_flags,
        "bonus_score": bonus_score,
        "interpretations": interpretations
    }


# ==========================================
# 1. MEWS CALCULATOR (Age + Pregnancy Aware)
# ==========================================
def calculate_mews(vitals: Dict[str, Any], age: int = 30, pregnant: bool = False) -> Dict[str, Any]:
    score = 0
    breakdown = []
    age_group = get_age_group(age)
    
    # ==========================================
    # PREGNANCY MEWS
    # ==========================================
    if pregnant:
        bp = vitals.get('systolic_bp', 110)
        if bp >= 160: score += 3; breakdown.append("Pregnancy: SBP ≥ 160 (+3)")
        elif bp >= 140: score += 2; breakdown.append("Pregnancy: SBP 140-159 (+2)")
        elif 90 <= bp < 140: pass
        elif 80 <= bp < 90: score += 1; breakdown.append("Pregnancy: SBP 80-89 (+1)")
        else: score += 3; breakdown.append("Pregnancy: SBP < 80 (+3)")
        
        hr = vitals.get('heart_rate', 85)
        if hr >= 130: score += 3; breakdown.append("Pregnancy: HR ≥ 130 (+3)")
        elif hr >= 110: score += 2; breakdown.append("Pregnancy: HR 110-129 (+2)")
        elif 70 <= hr < 110: pass
        elif 60 <= hr < 70: score += 1; breakdown.append("Pregnancy: HR 60-69 (+1)")
        else: score += 2; breakdown.append("Pregnancy: HR < 60 (+2)")
        
        rr = vitals.get('respiratory_rate', 18)
        if rr < 9: score += 2; breakdown.append("Pregnancy: RR < 9 (+2)")
        elif 15 <= rr <= 22: pass
        elif 23 <= rr <= 29: score += 2; breakdown.append("Pregnancy: RR 23-29 (+2)")
        elif rr >= 30: score += 3; breakdown.append("Pregnancy: RR ≥ 30 (+3)")
        
        temp_f = vitals.get('temperature_f', 98.6)
        temp_c = (temp_f - 32) * 5/9 if temp_f > 45 else temp_f
        if temp_c < 35: score += 2; breakdown.append("Pregnancy: Temp < 35C (+2)")
        elif temp_c > 38: score += 2; breakdown.append("Pregnancy: Temp > 38C (+2)")
        
        spo2 = vitals.get('spo2', 98)
        if spo2 < 90: score += 3; breakdown.append("Pregnancy: SpO2 < 90% (+3)")
        elif 90 <= spo2 <= 93: score += 2; breakdown.append("Pregnancy: SpO2 90-93% (+2)")
        elif 94 <= spo2 <= 95: score += 1; breakdown.append("Pregnancy: SpO2 94-95% (+1)")
        
        return {
            "score": score,
            "breakdown": breakdown,
            "age_group": age_group,
            "patient_type": "pregnant"
        }
    
    # ==========================================
    # PEDIATRIC MEWS
    # ==========================================
    if age_group in ["infant", "toddler", "child"]:
        rr = vitals.get('respiratory_rate', 16)
        hr = vitals.get('heart_rate', 80)
        bp = vitals.get('systolic_bp', 100)
        
        if age_group == "infant":
            if rr < 20: score += 2; breakdown.append("RR < 20 (+2)")
            elif 20 <= rr < 30: score += 1; breakdown.append("RR 20-29 (+1)")
            elif 30 <= rr <= 60: pass
            elif 61 <= rr <= 80: score += 2; breakdown.append("RR 61-80 (+2)")
            else: score += 3; breakdown.append("RR > 80 (+3)")
        elif age_group == "toddler":
            if rr < 20: score += 2; breakdown.append("RR < 20 (+2)")
            elif 20 <= rr < 24: score += 1; breakdown.append("RR 20-23 (+1)")
            elif 24 <= rr <= 40: pass
            elif 41 <= rr <= 60: score += 2; breakdown.append("RR 41-60 (+2)")
            else: score += 3; breakdown.append("RR > 60 (+3)")
        else:
            if rr < 15: score += 2; breakdown.append("RR < 15 (+2)")
            elif 15 <= rr < 20: score += 1; breakdown.append("RR 15-19 (+1)")
            elif 20 <= rr <= 30: pass
            elif 31 <= rr <= 40: score += 2; breakdown.append("RR 31-40 (+2)")
            else: score += 3; breakdown.append("RR > 40 (+3)")
        
        if age_group == "infant":
            if hr < 80: score += 3; breakdown.append("HR < 80 (+3)")
            elif 80 <= hr < 100: score += 1; breakdown.append("HR 80-99 (+1)")
            elif 100 <= hr <= 160: pass
            elif 161 <= hr <= 180: score += 2; breakdown.append("HR 161-180 (+2)")
            else: score += 3; breakdown.append("HR > 180 (+3)")
        elif age_group == "toddler":
            if hr < 70: score += 3; breakdown.append("HR < 70 (+3)")
            elif 70 <= hr < 90: score += 1; breakdown.append("HR 70-89 (+1)")
            elif 90 <= hr <= 150: pass
            elif 151 <= hr <= 170: score += 2; breakdown.append("HR 151-170 (+2)")
            else: score += 3; breakdown.append("HR > 170 (+3)")
        else:
            if hr < 60: score += 3; breakdown.append("HR < 60 (+3)")
            elif 60 <= hr < 80: score += 1; breakdown.append("HR 60-79 (+1)")
            elif 80 <= hr <= 120: pass
            elif 121 <= hr <= 140: score += 2; breakdown.append("HR 121-140 (+2)")
            else: score += 3; breakdown.append("HR > 140 (+3)")
        
        if age_group == "infant":
            if bp < 50: score += 3; breakdown.append("SBP < 50 (+3)")
            elif 50 <= bp < 70: score += 2; breakdown.append("SBP 50-69 (+2)")
            elif 70 <= bp <= 90: pass
            elif 91 <= bp <= 110: score += 1; breakdown.append("SBP 91-110 (+1)")
            else: score += 2; breakdown.append("SBP > 110 (+2)")
        elif age_group == "toddler":
            if bp < 60: score += 3; breakdown.append("SBP < 60 (+3)")
            elif 60 <= bp < 80: score += 2; breakdown.append("SBP 60-79 (+2)")
            elif 80 <= bp <= 100: pass
            elif 101 <= bp <= 120: score += 1; breakdown.append("SBP 101-120 (+1)")
            else: score += 2; breakdown.append("SBP > 120 (+2)")
        else:
            if bp < 70: score += 3; breakdown.append("SBP < 70 (+3)")
            elif 70 <= bp < 85: score += 2; breakdown.append("SBP 70-84 (+2)")
            elif 85 <= bp <= 110: pass
            elif 111 <= bp <= 130: score += 1; breakdown.append("SBP 111-130 (+1)")
            else: score += 2; breakdown.append("SBP > 130 (+2)")
        
        temp_f = vitals.get('temperature_f', 98.6)
        temp_c = (temp_f - 32) * 5/9 if temp_f > 45 else temp_f
        if temp_c < 35: score += 2; breakdown.append("Temp < 35C (+2)")
        elif temp_c > 38.4: score += 2; breakdown.append(f"Temp > 38.4C ({temp_f}F) (+2)")
        
        spo2 = vitals.get('spo2', 98)
        if spo2 < 90: score += 3; breakdown.append("SpO2 < 90% (+3)")
        elif 90 <= spo2 <= 93: score += 2; breakdown.append("SpO2 90-93% (+2)")
        elif 94 <= spo2 <= 95: score += 1; breakdown.append("SpO2 94-95% (+1)")
        
        return {
            "score": score,
            "breakdown": breakdown,
            "age_group": age_group,
            "patient_type": "pediatric"
        }
    
    # ==========================================
    # ADULT MEWS
    # ==========================================
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
    
    return {
        "score": score,
        "breakdown": breakdown,
        "age_group": age_group,
        "patient_type": "adult"
    }


# ==========================================
# 2. MANCHESTER TRIAGE & ROUTING (Lab-Aware)
# ==========================================
def determine_triage(
    symptoms: List[str],
    mews_score: int,
    facility: str,
    age: int = 30,
    pregnant: bool = False,
    lab_findings: Dict[str, Any] = None
) -> Dict[str, Any]:
    
    symptoms_str = " ".join(symptoms).lower()
    age_group = get_age_group(age)
    
    lab_result = interpret_lab_findings(lab_findings or {})
    lab_red_flags = lab_result["red_flags"]
    lab_bonus = lab_result["bonus_score"]
    
    effective_score = mews_score + lab_bonus
    
    p1_flags = ["crushing chest pain", "radiating to jaw", "diaphoresis",
                "severe respiratory distress", "unresponsive", "shock"]
    p2_flags = ["uncontrolled diabetes", "diabetic foot sore", "severe chronic anemia",
                "tachycardia", "high fever", "severe dehydration"]
    
    pediatric_p1 = ["convulsions", "seizures", "blue lips", "unconscious",
                    "not breathing", "stiff neck", "bulging fontanelle"]
    pediatric_p2 = ["persistent vomiting", "refusing to feed", "lethargy",
                    "irritability", "poor feeding", "sunken eyes"]
    
    pregnancy_p1 = [
        "severe headache", "blurring of vision", "vaginal bleeding",
        "severe abdominal pain", "convulsions", "seizures",
        "reduced fetal movement", "no fetal movement",
        "severe swelling", "difficulty breathing", "chest pain",
        "high bp", "hypertension"
    ]
    pregnancy_p2 = [
        "swelling of face", "swelling of hands", "swelling of feet",
        "mild headache", "protein in urine", "spotting",
        "persistent vomiting", "severe nausea", "abdominal discomfort"
    ]
    
    if age_group in ["infant", "toddler", "child"]:
        p1_flags += pediatric_p1
        p2_flags += pediatric_p2
    
    if pregnant:
        p1_flags += pregnancy_p1
        p2_flags += pregnancy_p2
    
    priority = "P4"
    reason = "Routine vitals, stable presentation."
    dept = "General Outpatient (OPD)"
    referral = None
    checklist = []
    
    if effective_score >= 5 or any(flag in symptoms_str for flag in p1_flags) or lab_red_flags:
        priority = "P1"
        
        lab_reason = ""
        if lab_red_flags:
            lab_reason = " | Lab: " + ", ".join(lab_red_flags)
        
        if pregnant:
            reason = "MATERNAL EMERGENCY: Critical condition. Immediate intervention required." + lab_reason
            dept = "Obstetrics & Gynecology (OB/GYN) - Emergency"
            checklist = [
                "Alert OB/GYN specialist immediately",
                "Monitor fetal heart rate (if applicable)",
                "Keep patient in left lateral position",
                "Prepare for emergency C-section if needed"
            ]
            if "PHC" in facility or "Primary" in facility:
                referral = "MATERNAL EMERGENCY: Transfer to DH/CHC with OB/GYN + NICU support immediately."
        elif age_group in ["infant", "toddler", "child"]:
            reason = "PEDIATRIC EMERGENCY: Critical condition. Immediate intervention required." + lab_reason
            dept = "Pediatric Emergency / NICU-PICU"
            checklist = [
                "Alert pediatric specialist immediately",
                "Monitor vitals every 10 mins",
                "Ensure IV access",
                "Prepare age-appropriate medications"
            ]
            if "PHC" in facility or "Primary" in facility:
                referral = "PEDIATRIC EMERGENCY: Transfer to DH/CHC with Pediatric ICU support."
        else:
            reason = "Critical emergency. Immediate intervention required." + lab_reason
            dept = "Emergency Resuscitation Bay / ICU"
            checklist = [
                "Proceed with standard vitals monitoring",
                "Keep patient hydrated and monitor vitals every 15 mins",
                "Prepare ABHA digital health record"
            ]
            if lab_red_flags:
                checklist.append("Review lab report and act accordingly")
            if "PHC" in facility or "Primary" in facility:
                referral = "INTER-FACILITY REFERRAL RECOMMENDED: Transfer to District Hospital (DH) or CHC."
    
    elif effective_score >= 3 or any(flag in symptoms_str for flag in p2_flags):
        priority = "P2"
        if pregnant:
            reason = "High-risk pregnancy. Urgent OB/GYN review needed."
            dept = "Obstetrics & Gynecology (OB/GYN)"
            checklist = [
                "Monitor BP and fetal movements",
                "Check urine protein",
                "Prepare for possible admission"
            ]
        else:
            reason = "Urgent condition requiring prompt review."
            dept = "Urgent Care / Specialist OPD"
            checklist = ["Monitor vitals every 30 minutes", "Prepare for specialist consultation"]
    
    elif effective_score >= 1:
        priority = "P3"
        reason = "Semi-urgent. Requires attention within 30-60 mins."
        dept = "General Outpatient (OPD)"
        checklist = ["Provide symptomatic relief", "Schedule follow-up in 24-48 hours"]
    
    return {
        "priority_level": priority,
        "priority_label": f"{priority} {'EMERGENCY' if priority=='P1' else 'URGENT' if priority=='P2' else 'SEMI-URGENT' if priority=='P3' else 'ROUTINE'}",
        "triage_reason": reason,
        "recommended_department": dept,
        "referral_advice": referral,
        "immediate_checklist": checklist,
        "lab_interpretations": lab_result["interpretations"]
    }


# ==========================================
# 3. MAIN ORCHESTRATOR (Lab-Aware)
# ==========================================
def run_triage_assessment(patient_data: Dict[str, Any]) -> Dict[str, Any]:
    vitals = patient_data.get("vitals", {})
    symptoms = patient_data.get("symptoms", [])
    facility = patient_data.get("facility", "Primary Health Centre (PHC)")
    demographics = patient_data.get("demographics", {})
    lab_findings = patient_data.get("lab_findings", {})
    patient_category = patient_data.get("patient_category", "None")
    
    age = demographics.get("age", 30)
    if not isinstance(age, (int, float)):
        age = 30
    age = int(age)
    
    # ==========================================
    # PATIENT TYPE DETERMINE (No is_pregnant/trimester)
    # ==========================================
    if patient_category == "Pregnancy":
        pregnant = True
        patient_type = "pregnant"
    elif patient_category == "Child":
        pregnant = False
        patient_type = "pediatric"
    else:
        pregnant = False
        if age < 12:
            patient_type = "pediatric"
        else:
            patient_type = "adult"
    
    # MEWS CALCULATE
    mews_result = calculate_mews(vitals, age, pregnant)
    if patient_category in ["Pregnancy", "Child"]:
        mews_result["patient_type"] = patient_type
    
    # TRIAGE DECISION
    triage_result = determine_triage(
        symptoms, 
        mews_result["score"], 
        facility, 
        age, 
        pregnant,
        lab_findings
    )
    
    # MISSING INFO
    missing_info = []
    symptoms_str = " ".join(symptoms).lower()
    
    if pregnant:
        if "weeks" not in symptoms_str and "trimester" not in symptoms_str:
            missing_info.append("Gestational age (weeks of pregnancy)")
        if "fetal movement" not in symptoms_str:
            missing_info.append("Fetal movement status")
        if "bp" not in symptoms_str and "blood pressure" not in symptoms_str:
            missing_info.append("Current BP reading (pre-eclampsia screening)")
        if "urine" not in symptoms_str and "protein" not in symptoms_str:
            missing_info.append("Urine protein test (pre-eclampsia screening)")
    else:
        if "cabg" not in symptoms_str:
            missing_info.append("Prior history of cardiac interventions / CABG")
        if "aspirin" not in symptoms_str and "meal" not in symptoms_str:
            missing_info.append("Time of last meal / aspirin intake")
    
    # QUESTIONS
    if pregnant:
        questions = [
            "How many weeks pregnant are you?",
            "Is the baby moving normally? Any reduced movement?",
            "Any bleeding, fluid leakage, or severe abdominal pain?",
            "Any swelling of face, hands, or feet?",
            "Any history of high BP, diabetes, or previous pregnancy complications?"
        ]
    elif patient_type == "pediatric":
        questions = [
            "Is the child feeding normally?",
            "Any decrease in activity or alertness?",
            "Any breathing difficulty or chest retractions?",
            "Is the child passing urine normally?",
            "Any rash, convulsions, or unusual movements?"
        ]
    else:
        questions = [
            "Have you noticed any dizziness, blurred vision, or fainting?",
            "Can you keep fluids down, or is there persistent nausea/vomiting?",
            "Are there any other family or work members experiencing identical symptoms?"
        ]
    
    # ==========================================
    # FINAL RESPONSE (is_pregnant aur trimester HATA DIYE)
    # ==========================================
    return {
        "status": "success",
        "mews_score": mews_result["score"],
        "mews_breakdown": mews_result["breakdown"],
        "age_group": mews_result["age_group"],
        "patient_type": mews_result["patient_type"],
        "triage_priority": triage_result["priority_label"],
        "triage_reason": triage_result["triage_reason"],
        "lab_interpretations": triage_result.get("lab_interpretations", []),
        "routing": {
            "recommended_department": triage_result["recommended_department"],
            "referral_advice": triage_result["referral_advice"],
            "immediate_checklist": triage_result["immediate_checklist"]
        },
        "identified_missing_info": missing_info,
        "prioritized_questions": questions,
        "disclaimer": "STATUTORY NON-DIAGNOSTIC HEALTHCARE ADVISORY NOTICE: CLINICAL ADVISORY ONLY."
    }