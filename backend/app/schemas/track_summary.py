from pydantic import BaseModel


class TrackStatusSummary(BaseModel):
    total: int
    by_status: dict[str, int]
