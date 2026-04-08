import logging
from fastapi import FastAPI, Header, HTTPException, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from backend.db import engine, get_db, Base
from backend.models import Submission, ApiKey
from backend.schemas import IngestRequest, IngestResponse, SubmissionResponse
from backend.rate_limiter import check_rate_limit
from backend.tasks import process_submission
from backend.config import MAX_INPUT_LENGTH

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

Base.metadata.create_all(bind=engine)

app = FastAPI(title="AI Content Processing Pipeline", version="1.0.0")


def get_user(x_api_key: str = Header(...), db: Session = Depends(get_db)) -> ApiKey:
    api_key = db.query(ApiKey).filter(ApiKey.key == x_api_key, ApiKey.is_active == 1).first()
    if not api_key:
        raise HTTPException(status_code=401, detail="invalid or inactive api key")
    return api_key


@app.post("/api/ingest", response_model=IngestResponse)
def ingest(
    body: IngestRequest,
    api_key: ApiKey = Depends(get_user),
    db: Session = Depends(get_db),
):
    limit_info = check_rate_limit(api_key.key)
    if not limit_info["allowed"]:
        return JSONResponse(
            status_code=429,
            content={"detail": "rate limit exceeded"},
            headers={
                "X-RateLimit-Limit": str(limit_info["limit"]),
                "X-RateLimit-Remaining": str(limit_info["remaining"]),
                "X-RateLimit-Reset": str(limit_info["reset"]),
            },
        )

    text = body.text.strip()
    if len(text) > MAX_INPUT_LENGTH:
        raise HTTPException(status_code=400, detail=f"input exceeds {MAX_INPUT_LENGTH} characters")

    if len(text) < 10:
        raise HTTPException(status_code=400, detail="input too short to extract anything useful")

    if body.idempotency_key:
        existing = db.query(Submission).filter(
            Submission.user_id == api_key.user_id,
            Submission.idempotency_key == body.idempotency_key,
        ).first()
        if existing:
            return IngestResponse(
                submission_id=existing.id,
                status=existing.status,
                message="already submitted with this idempotency key",
            )

    sub = Submission(
        user_id=api_key.user_id,
        raw_text=text,
        idempotency_key=body.idempotency_key,
        status="queued",
    )
    db.add(sub)
    db.commit()
    db.refresh(sub)

    process_submission.delay(sub.id)

    return IngestResponse(
        submission_id=sub.id,
        status="queued",
        message="submission queued for processing",
    )


@app.get("/api/status/{submission_id}", response_model=SubmissionResponse)
def get_status(
    submission_id: str,
    api_key: ApiKey = Depends(get_user),
    db: Session = Depends(get_db),
):
    sub = db.query(Submission).filter(
        Submission.id == submission_id,
        Submission.user_id == api_key.user_id,
    ).first()
    if not sub:
        raise HTTPException(status_code=404, detail="submission not found")

    return SubmissionResponse(
        id=sub.id,
        status=sub.status,
        result=sub.result,
        error=sub.error,
        retry_count=sub.retry_count,
        llm_provider=sub.llm_provider,
        created_at=str(sub.created_at) if sub.created_at else None,
        completed_at=str(sub.completed_at) if sub.completed_at else None,
    )


@app.get("/api/submissions")
def list_submissions(
    api_key: ApiKey = Depends(get_user),
    db: Session = Depends(get_db),
):
    subs = db.query(Submission).filter(
        Submission.user_id == api_key.user_id,
    ).order_by(Submission.created_at.desc()).limit(50).all()

    return [
        SubmissionResponse(
            id=s.id,
            status=s.status,
            result=s.result,
            error=s.error,
            retry_count=s.retry_count,
            llm_provider=s.llm_provider,
            created_at=str(s.created_at) if s.created_at else None,
            completed_at=str(s.completed_at) if s.completed_at else None,
        )
        for s in subs
    ]


@app.get("/health")
def health():
    return {"status": "ok"}
