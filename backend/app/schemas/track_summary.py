from pydantic import BaseModel


class TrackStatusSummary(BaseModel):
    total: int
    by_status: dict[str, int]
    by_pipeline_stage: dict[str, int]
