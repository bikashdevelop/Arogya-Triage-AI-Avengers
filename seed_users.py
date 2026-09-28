from database import SessionLocal, engine
from passlib.context import CryptContext
import models

models.Base.metadata.create_all(bind=engine)

pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
db = SessionLocal()

if db.query(models.User).count() > 0:
    print("Users already exist. Delete triage.db to reset.")
else:
    db.add_all([
            models.User(
            username="admin1",
            password_hash=pwd.hash("admin123"),
            role="admin",
            full_name="System Admin",
            facility_id=None,
            department=None,
        ),
        models.User(
            username="nurse1",
            password_hash=pwd.hash("nurse123"),
            role="nurse",
            full_name="Nurse Priya",
            facility_id="PHC-BBSR-001",
        ),
        models.User(
            username="dr_jena",
            password_hash=pwd.hash("doctor123"),
            role="doctor",
            full_name="Dr. B. K. Jena",
            department="Emergency",
            facility_id="PHC-BBSR-001",
        ),
        models.User(
            username="dr_priya",
            password_hash=pwd.hash("doctor123"),
            role="doctor",
            full_name="Dr. Priya Mohapatra",
            department="General OPD",
            facility_id="PHC-CTC-005",
        ),
    ])
    db.commit()
    print("Created:")
    print("  admin1 / admin123        (System Admin)")
    print("  nurse1 / nurse123        (PHC-BBSR-001)")
    print("  dr_jena / doctor123      (PHC-BBSR-001, Emergency)")
    print("  dr_priya / doctor123     (PHC-CTC-005, OPD)")

db.close()