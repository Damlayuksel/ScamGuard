from pydantic import BaseModel, Field

from app.models import ScanLevel

MAX_TEXT_LENGTH = 5000


class ScanRequest(BaseModel):
    text: str = Field(min_length=1, max_length=MAX_TEXT_LENGTH)


class ScannedLink(BaseModel):
    domain: str = Field(description="Registered domain only, never the full URL.")
    score: int
    reasons: list[str]


class ScanResponse(BaseModel):
    level: ScanLevel
    label: str
    message: str
    score: int
    reasons: list[str]
    links: list[ScannedLink]
    advice: list[str]
