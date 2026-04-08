"""
Seeds test API keys into the database.
Run once: python test.py
"""
from backend.db import engine, SessionLocal, Base
from backend.models import ApiKey

Base.metadata.create_all(bind=engine)

db = SessionLocal()

test_keys = [
    {"key": "test-key-user-1", "user_id": "user_1", "tier": "free"},
    {"key": "test-key-user-2", "user_id": "user_2", "tier": "free"},
]

for kd in test_keys:
    exists = db.query(ApiKey).filter(ApiKey.key == kd["key"]).first()
    if not exists:
        db.add(ApiKey(**kd))
        print(f"created api key: {kd['key']} -> {kd['user_id']}")
    else:
        print(f"already exists: {kd['key']}")

db.commit()
db.close()
print("done")
