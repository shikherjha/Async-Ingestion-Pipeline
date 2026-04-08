import logging
from datetime import datetime, timezone
from backend.celery_app import celery_app
from backend.db import SessionLocal
from backend.models import Submission
from backend.llm import extract
from backend.validation import validate_extracted
from backend.config import MAX_LLM_RETRIES

log = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    max_retries=MAX_LLM_RETRIES,
    default_retry_delay=5,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=60,
)
def process_submission(self, submission_id: str):
    db = SessionLocal()
    try:
        sub = db.query(Submission).filter(Submission.id == submission_id).first()
        if not sub:
            log.error(f"submission {submission_id} not found")
            return

        sub.status = "processing"
        sub.started_at = datetime.now(timezone.utc)
        sub.retry_count = self.request.retries
        db.commit()

        raw_data, provider = extract(sub.raw_text)
        sub.llm_provider = provider

        parsed, validation_errors = validate_extracted(raw_data)

        if parsed is None:
            sub.status = "failed_validation"
            sub.error = "; ".join(validation_errors)
            sub.completed_at = datetime.now(timezone.utc)
            db.commit()
            return

        if validation_errors:
            log.warning(f"soft validation issues for {submission_id}: {validation_errors}")

        sub.status = "completed"
        sub.result = parsed.model_dump()
        sub.error = "; ".join(validation_errors) if validation_errors else None
        sub.completed_at = datetime.now(timezone.utc)
        db.commit()

    except Exception as e:
        db.rollback()
        sub_check = db.query(Submission).filter(Submission.id == submission_id).first()
        if sub_check:
            sub_check.retry_count = self.request.retries
            if self.request.retries >= MAX_LLM_RETRIES:
                sub_check.status = "failed_llm"
                sub_check.error = str(e)[:500]
                sub_check.completed_at = datetime.now(timezone.utc)
                db.commit()
                log.error(f"submission {submission_id} moved to DLQ after {MAX_LLM_RETRIES} retries: {e}")
                return
            db.commit()
        raise
    finally:
        db.close()
