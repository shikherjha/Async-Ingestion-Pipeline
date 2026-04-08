import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, DateTime, Integer, Index, JSON
from backend.db import Base


def _utcnow():
    return datetime.now(timezone.utc)


def _uuid():
    return str(uuid.uuid4())


class Submission(Base):
    __tablename__ = "submissions"

    id = Column(String, primary_key=True, default=_uuid)
    user_id = Column(String, nullable=False, index=True)
    idempotency_key = Column(String, nullable=True)
    raw_text = Column(Text, nullable=False)

    status = Column(String, nullable=False, default="queued")
    # queued | processing | completed | failed_llm | failed_validation | failed_request

    result = Column(JSON, nullable=True)
    error = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    llm_provider = Column(String, nullable=True)

    created_at = Column(DateTime, default=_utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    __table_args__ = (
        Index("ix_user_idempotency", "user_id", "idempotency_key", unique=True),
    )


class ApiKey(Base):
    __tablename__ = "api_keys"

    key = Column(String, primary_key=True)
    user_id = Column(String, nullable=False, unique=True)
    tier = Column(String, default="free")
    created_at = Column(DateTime, default=_utcnow)
    is_active = Column(Integer, default=1)
