import json

from app.models.job import Job


def job_payload(job: Job) -> dict[str, object]:
    if not job.payload:
        return {}
    try:
        data = json.loads(job.payload)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}
