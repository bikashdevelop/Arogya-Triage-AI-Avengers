from database import SessionLocal, engine, Base
import models
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

USERS = [
    {"username": "admin", "password": "adminpassword123", "role": "admin",
     "full_name": "System Admin", "facility_id": "FAC-001",
     "department": "Administration", "years_experience": 0,
     "avg_consultation_mins": 0, "max_load": 0},
    {"username": "nurse1", "password": "nurse123", "role": "nurse",
     "full_name": "Nurse Priya", "facility_id": "FAC-001",
     "department": None, "years_experience": 0,
     "avg_consultation_mins": 5, "max_load": 100},
    {"username": "dr_jena", "password": "doctor123", "role": "doctor",
     "full_name": "Dr. B. K. Jena", "facility_id": "FAC-001",
     "department": "Emergency", "years_experience": 15,
     "avg_consultation_mins": 8, "max_load": 15},
    {"username": "dr_mohanty", "password": "doctor123", "role": "doctor",
     "full_name": "Dr. R. Mohanty", "facility_id": "FAC-001",
     "department": "General Medicine", "years_experience": 16,
     "avg_consultation_mins": 12, "max_load": 20},
    {"username": "dr_panda", "password": "doctor123", "role": "doctor",
     "full_name": "Dr. K. Panda", "facility_id": "FAC-001",
     "department": "Orthopedics", "years_experience": 18,
     "avg_consultation_mins": 15, "max_load": 12},
    {"username": "dr_swain", "password": "doctor123", "role": "doctor",
     "full_name": "Dr. N. Swain", "facility_id": "FAC-001",
     "department": "Obstetrics & Gynecology", "years_experience": 13,
     "avg_consultation_mins": 18, "max_load": 10},
    {"username": "dr_das", "password": "doctor123", "role": "doctor",
     "full_name": "Dr. P. Das", "facility_id": "FAC-001",
     "department": "Cardiology", "years_experience": 12,
     "avg_consultation_mins": 10, "max_load": 8},
    {"username": "dr_patnaik", "password": "doctor123", "role": "doctor",
     "full_name": "Dr. S. Patnaik", "facility_id": "FAC-001",
     "department": "Pediatrics", "years_experience": 14,
     "avg_consultation_mins": 10, "max_load": 15},
    {"username": "chemist1", "password": "chemist123", "role": "chemist",
     "full_name": "Chemist Ramesh", "facility_id": "FAC-001",
     "department": "Pharmacy", "years_experience": 0,
     "avg_consultation_mins": 5, "max_load": 100},
]


def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    for u in USERS:
        existing = db.query(models.User).filter(models.User.username == u["username"]).first()
        if existing:
            existing.password_hash = pwd_context.hash(u["password"])
            for k in ("role", "full_name", "facility_id", "department"):
                setattr(existing, k, u[k])
            existing.is_on_duty = True
            existing.current_load = 0
            existing.max_load = u["max_load"]
            existing.years_experience = u["years_experience"]
            existing.total_assigned_today = 0
            existing.avg_consultation_mins = u["avg_consultation_mins"]
            print(f"Updated: {u['username']:12} | {u['department'] or 'N/A':28}")
        else:
            db.add(models.User(
                username=u["username"], password_hash=pwd_context.hash(u["password"]),
                role=u["role"], full_name=u["full_name"], facility_id=u["facility_id"],
                department=u["department"], is_on_duty=True, current_load=0,
                max_load=u["max_load"], years_experience=u["years_experience"],
                total_assigned_today=0, avg_consultation_mins=u["avg_consultation_mins"],
            ))
            print(f"Created: {u['username']:12} | {u['department'] or 'N/A':28}")
    db.commit()
    db.close()
    print("\nSeeding complete!")


if __name__ == "__main__":
    seed()