from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum


class SubmissionStatus(str, Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED_LLM = "failed_llm"
    FAILED_VALIDATION = "failed_validation"
    FAILED_REQUEST = "failed_request"


class IngestRequest(BaseModel):
    text: str = Field(..., min_length=10, max_length=8000)
    idempotency_key: Optional[str] = None


class IngestResponse(BaseModel):
    submission_id: str
    status: str
    message: str


class ExtractedData(BaseModel):
    company: str = Field(..., min_length=2)
    role: str
    stipend: Optional[str] = None
    batch: Optional[str] = None
    location: Optional[str] = None
    employment_type: Optional[str] = None
    domains: Optional[List[str]] = None
    tech_keywords: Optional[List[str]] = None
    summary: Optional[str] = None
    application_link: Optional[str] = None
    contact_email: Optional[str] = None


class SubmissionResponse(BaseModel):
    id: str
    status: str
    result: Optional[dict] = None
    error: Optional[str] = None
    retry_count: int = 0
    llm_provider: Optional[str] = None
    created_at: Optional[str] = None
    completed_at: Optional[str] = None

    class Config:
        from_attributes = True
