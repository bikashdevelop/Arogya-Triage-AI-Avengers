from database import SessionLocal, engine
from passlib.context import CryptContext
import models

models.Base.metadata.create_all(bind=engine)

pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
db = SessionLocal()

if db.query(models.User).count() > 0:
    print("Users already exist.")
else:
    db.add_all([
        models.User(
            username="nurse1",
            password_hash=pwd.hash("nurse123"),
            role="nurse",
            full_name="Nurse Priya",
        ),
        models.User(
            username="dr_jena",
            password_hash=pwd.hash("doctor123"),
            role="doctor",
            full_name="Dr. B. K. Jena",
        ),
    ])
    db.commit()
    print("Created: nurse1/nurse123, dr_jena/doctor123")

db.close()