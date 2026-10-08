from database import engine
import models

print("Deleting old tables...")
models.Base.metadata.drop_all(bind=engine)

print("Creating new tables with updated columns...")
models.Base.metadata.create_all(bind=engine)

print("✅ Database successfully reset! You can now restart the backend.")