import re
from backend.schemas import ExtractedData


BATCH_PATTERN = re.compile(r"^20[2-3]\d$")


def validate_extracted(data: dict) -> tuple[ExtractedData | None, list[str]]:
    errors = []

    try:
        parsed = ExtractedData(**data)
    except Exception as e:
        return None, [f"schema: {str(e)}"]

    if parsed.company and len(parsed.company.strip()) < 2:
        errors.append("company name too short")

    if parsed.stipend:
        has_digits = any(c.isdigit() for c in parsed.stipend)
        is_unpaid = "unpaid" in parsed.stipend.lower()
        if not has_digits and not is_unpaid:
            errors.append(f"stipend looks invalid: {parsed.stipend}")

    if parsed.batch:
        clean_batch = parsed.batch.strip()
        if not BATCH_PATTERN.match(clean_batch):
            errors.append(f"batch format invalid: {clean_batch}")

    return parsed, errors
