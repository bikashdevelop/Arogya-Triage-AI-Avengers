from database import SessionLocal
import models
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# 👇 EXACT ACCOUNTS YOU NEED
USERS_TO_CREATE = [
    {"username": "dr_jena",    "password": "doctor123",    "role": "doctor",    "full_name": "Dr. B. K. Jena", "department": "General Medicine"},
    {"username": "nurse1",     "password": "nurse123",     "role": "nurse",     "full_name": "Nurse 1"},
    {"username": "admin",      "password": "admin123",     "role": "admin",     "full_name": "Admin"},
    {"username": "reception1", "password": "reception123", "role": "reception", "full_name": "Reception 1"},
    {"username": "chemist1",   "password": "chemist123",   "role": "chemist",   "full_name": "Chemist 1"},
]

db = SessionLocal()
for u in USERS_TO_CREATE:
    existing = db.query(models.User).filter(models.User.username == u["username"]).first()
    if existing:
        existing.password_hash = pwd_context.hash(u["password"])
        print(f"✅ Updated {u['username']}")
    else:
        db.add(models.User(
            username=u["username"],
            password_hash=pwd_context.hash(u["password"]),
            role=u["role"],
            full_name=u["full_name"],
            facility_id="FAC-001",
            department=u.get("department")
        ))
        print(f"✅ Created {u['username']}")

db.commit()
db.close()
print("🎉 All accounts restored! You can now log in.")