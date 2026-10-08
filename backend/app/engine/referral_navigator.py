"""
Referral Navigator Engine
Provides a recommendation for referral based on symptoms, vitals, and facilities.
"""

class ReferralRecommendation:
    def __init__(self, priority="P3", priority_label="ROUTINE",
                 urgency_reasons=None, service_reasons=None, facility_reasons=None,
                 suggested_service_code="GEN_MED", suggested_service_name="General Medicine",
                 suggested_facility_id=None, suggested_facility_name=None,
                 suggested_facility_type=None,
                 availability_confidence="UNVERIFIED", last_verified_at=None,
                 fallback_facilities=None, emergency_pathway=False,
                 routing_confidence="LOW"):
        
        self.priority = priority
        self.priority_label = priority_label
        self.urgency_reasons = urgency_reasons or []
        self.service_reasons = service_reasons or []
        self.facility_reasons = facility_reasons or []
        self.suggested_service_code = suggested_service_code
        self.suggested_service_name = suggested_service_name
        self.suggested_facility_id = suggested_facility_id
        self.suggested_facility_name = suggested_facility_name
        self.suggested_facility_type = suggested_facility_type
        self.availability_confidence = availability_confidence
        self.last_verified_at = last_verified_at
        self.fallback_facilities = fallback_facilities or []
        self.emergency_pathway = emergency_pathway
        self.routing_confidence = routing_confidence

    def to_dict(self):
        return {
            "priority": self.priority,
            "priority_label": self.priority_label,
            "urgency_reasons": self.urgency_reasons,
            "service_reasons": self.service_reasons,
            "facility_reasons": self.facility_reasons,
            "suggested_service_code": self.suggested_service_code,
            "suggested_service_name": self.suggested_service_name,
            "suggested_facility_id": self.suggested_facility_id,
            "suggested_facility_name": self.suggested_facility_name,
            "suggested_facility_type": self.suggested_facility_type,
            "availability_confidence": self.availability_confidence,
            "last_verified_at": self.last_verified_at,
            "fallback_facilities": self.fallback_facilities,
            "emergency_pathway": self.emergency_pathway,
            "routing_confidence": self.routing_confidence,
        }


def recommend_referral(symptoms_text: str, category: str, age: int, vitals: dict,
                       facilities: list, capabilities_by_facility: dict,
                       current_facility_type: str) -> ReferralRecommendation:
    """
    Basic rule-based referral recommendation engine.
    """
    symptoms_lower = (symptoms_text or "").lower()
    
    # Defaults
    priority = "P3"
    priority_label = "ROUTINE"
    urgency_reasons = []
    emergency_pathway = False
    suggested_service_code = "GEN_MED"
    suggested_service_name = "General Medicine"
    suggested_facility_id = None
    suggested_facility_name = None
    routing_confidence = "MEDIUM"

    # 1. Check for Emergency Red Flags
    red_flags = ["chest pain", "breathless", "unconscious", "stroke", "severe bleeding", "accident"]
    if any(flag in symptoms_lower for flag in red_flags):
        priority = "P1"
        priority_label = "EMERGENCY"
        urgency_reasons.append("Red flag symptoms detected in triage narrative")
        emergency_pathway = True

    # 2. Determine Suggested Service
    if any(k in symptoms_lower for k in ["fracture", "bone", "injury", "sprain"]):
        suggested_service_code = "ORTHO"
        suggested_service_name = "Orthopedics"
    elif "pregnancy" in (category or "").lower():
        suggested_service_code = "OBGYN"
        suggested_service_name = "Obstetrics & Gynecology"
    elif any(k in symptoms_lower for k in ["chest", "heart", "palpitation"]):
        suggested_service_code = "CARDIO"
        suggested_service_name = "Cardiology"

    # 3. Determine Facility (if emergency, try to find an emergency-capable facility)
    if emergency_pathway and facilities:
        for f in facilities:
            if f.get("emergency_capable"):
                suggested_facility_id = f.get("id")
                suggested_facility_name = f.get("facility_name")
                routing_confidence = "HIGH"
                break

    return ReferralRecommendation(
        priority=priority,
        priority_label=priority_label,
        urgency_reasons=urgency_reasons,
        suggested_service_code=suggested_service_code,
        suggested_service_name=suggested_service_name,
        suggested_facility_id=suggested_facility_id,
        suggested_facility_name=suggested_facility_name,
        routing_confidence=routing_confidence,
        emergency_pathway=emergency_pathway
    )