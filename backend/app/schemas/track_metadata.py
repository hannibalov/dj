from pydantic import BaseModel, Field


class TrackMetadataUpdate(BaseModel):
    artist: str = Field(min_length=1, max_length=512)
    title: str = Field(min_length=1, max_length=512)
