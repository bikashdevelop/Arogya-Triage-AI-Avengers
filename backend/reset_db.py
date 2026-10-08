from database import engine, Base
from sqlalchemy import text
import models

print("Wiping schema...")
with engine.connect() as conn:
    conn.execute(text("DROP SCHEMA public CASCADE"))
    conn.execute(text("CREATE SCHEMA public"))
    conn.commit()
print("Schema wiped.")

print("Creating tables...")
Base.metadata.create_all(bind=engine)
print("Tables created.")