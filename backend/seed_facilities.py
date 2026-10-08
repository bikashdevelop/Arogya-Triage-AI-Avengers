from database import SessionLocal, engine
import models
from datetime import datetime


def seed():
    models.Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    if db.query(models.Facility).count() > 0:
        print("Facilities already seeded.")
        db.close()
        return

    now = datetime.utcnow()

    facilities_data = [
        {"code": "AAM-PHC-KAL", "name": "Kalyanpur AAM-PHC", "type": "PHC",
         "district": "Ganjam", "emergency": False,
         "caps": [("GEN_MED", "consultation", "available"),
                  ("EMERGENCY", "stabilization", "available")]},
        {"code": "CHC-CHAND", "name": "Chandipur CHC", "type": "CHC",
         "district": "Ganjam", "emergency": True,
         "caps": [("GEN_MED", "consultation", "available"),
                  ("ORTHO", "consultation", "limited"),
                  ("EMERGENCY", "stabilization", "available")]},
        {"code": "FRU-BAN", "name": "Banapur FRU-CHC", "type": "FRU_CHC",
         "district": "Ganjam", "emergency": True,
         "caps": [("OBGYN", "definitive", "available"),
                  ("SURGERY", "definitive", "available"),
                  ("EMERGENCY", "definitive", "available")]},
        {"code": "DHH-GAN", "name": "District HQ Hospital, Ganjam", "type": "DHH",
         "district": "Ganjam", "emergency": True,
         "caps": [("GEN_MED", "definitive", "available"),
                  ("OBGYN", "definitive", "available"),
                  ("PAEDS", "definitive", "available"),
                  ("SURGERY", "definitive", "available"),
                  ("ORTHO", "definitive", "available"),
                  ("EMERGENCY", "definitive", "available")]},
        {"code": "MCH-BBS", "name": "Medical College Hospital, Bhubaneswar",
         "type": "MEDICAL_COLLEGE", "district": "Khordha", "emergency": True,
         "caps": [("GEN_MED", "definitive", "available"),
                  ("OBGYN", "definitive", "available"),
                  ("PAEDS", "definitive", "available"),
                  ("SURGERY", "definitive", "available"),
                  ("ORTHO", "definitive", "available"),
                  ("EMERGENCY", "definitive", "available")]},
    ]

    for f in facilities_data:
        fac = models.Facility(
            facility_code=f["code"], facility_name=f["name"],
            facility_type=f["type"], district=f["district"],
            emergency_capable=f["emergency"],
            operational_status="open", last_verified_at=now,
        )
        db.add(fac)
        db.flush()
        for svc, lvl, avail in f["caps"]:
            db.add(models.FacilityCapability(
                facility_id=fac.id, service_code=svc,
                capability_level=lvl, availability_status=avail,
                last_verified_at=now,
            ))

    db.commit()
    db.close()
    print("Seeded 5 facilities.")


if __name__ == "__main__":
    seed()