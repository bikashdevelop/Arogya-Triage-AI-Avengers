"""
doctor_assigner.py — Multi-factor explainable doctor assignment engine.
"""
from typing import List, Dict, Optional

WEIGHTS = {"load": 40, "fairness": 25, "experience": 15, "freshness": 10, "avg_speed": 10}


def _priority_weight(priority):
    if priority in ("P1", "P2"):
        return {"load": 30, "fairness": 15, "experience": 35, "freshness": 10, "avg_speed": 10}
    return WEIGHTS


def _is_available(doctor, required_department, priority):
    if not doctor.is_on_duty or doctor.role != "doctor":
        return False
    if priority == "P1":
        return True
    if required_department and doctor.department != required_department:
        return False
    if doctor.current_load >= doctor.max_load:
        return False
    return True


def _score_doctor(doctor, required_department, priority, all_candidates, max_assigned):
    w = _priority_weight(priority)
    reasons = []
    score = 0.0

    load_ratio = doctor.current_load / max(doctor.max_load, 1)
    ls = (1 - load_ratio) * w["load"]
    score += ls
    reasons.append(f"Load: {doctor.current_load}/{doctor.max_load} ({ls:.1f}/{w['load']} pts)")

    if max_assigned > 0:
        fs = (1 - (doctor.total_assigned_today or 0) / max_assigned) * w["fairness"]
    else:
        fs = w["fairness"]
    score += fs
    reasons.append(f"Fairness: {doctor.total_assigned_today or 0} assigned today ({fs:.1f}/{w['fairness']} pts)")

    if priority in ("P1", "P2"):
        es = min(doctor.years_experience or 0, 20) / 20 * w["experience"]
        score += es
        reasons.append(f"Experience: {doctor.years_experience or 0}y for {priority} ({es:.1f}/{w['experience']} pts)")

    fresh = w["freshness"] if doctor.current_load == 0 else w["freshness"] * 0.5
    score += fresh
    reasons.append(f"Freshness: {'idle' if doctor.current_load == 0 else 'has load'} ({fresh:.1f} pts)")

    speed = doctor.avg_consultation_mins or 10
    ss = (1 - min(speed, 30) / 30) * w["avg_speed"]
    score += ss
    reasons.append(f"Speed: {speed} min/consult ({ss:.1f}/{w['avg_speed']} pts)")

    if priority == "P1" and doctor.current_load >= doctor.max_load:
        score -= 15
        reasons.append("WARNING: P1 OVERRIDE - doctor at capacity")

    return score, reasons


def assign_doctor(doctors, required_department, priority, facility_id=None):
    pool = [d for d in doctors if not facility_id or d.facility_id == facility_id]
    candidates = [d for d in pool if _is_available(d, required_department, priority)]
    fallback_used = None

    if not candidates and priority not in ("P1", "P2"):
        gm = [d for d in pool if _is_available(d, "General Medicine", priority)]
        if gm:
            candidates = gm
            fallback_used = "general_medicine"

    if not candidates and priority == "P1":
        crit = [d for d in pool if d.is_on_duty and d.role == "doctor"]
        if crit:
            candidates = crit
            fallback_used = "p1_override"

    if not candidates:
        return {
            "chosen_doctor": None, "score": 0,
            "reasons": [f"No on-duty doctor for {required_department or 'any dept'} (priority {priority}). Escalate."],
            "candidate_scores": [], "fallback_used": "escalate",
            "total_considered": len(pool),
        }

    max_assigned = max((d.total_assigned_today or 0) for d in candidates)
    scored = []
    for doc in candidates:
        s, r = _score_doctor(doc, required_department, priority, candidates, max_assigned)
        scored.append({"doctor_id": doc.id, "name": doc.full_name,
                       "department": doc.department, "current_load": doc.current_load,
                       "max_load": doc.max_load, "score": round(s, 2), "reasons": r})

    scored.sort(key=lambda x: x["score"], reverse=True)
    winner = scored[0]
    chosen = next(d for d in candidates if d.id == winner["doctor_id"])

    return {"chosen_doctor": chosen, "score": winner["score"],
            "reasons": winner["reasons"], "candidate_scores": scored,
            "fallback_used": fallback_used, "total_considered": len(candidates)}


def estimate_wait(doctor, priority):
    return (doctor.current_load or 0) * (doctor.avg_consultation_mins or 10)