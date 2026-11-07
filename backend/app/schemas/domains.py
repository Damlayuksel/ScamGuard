from pydantic import BaseModel, Field


class DomainReportRequest(BaseModel):
    domain: str = Field(min_length=3, max_length=2048, description="Domain or link to report.")


class DomainReportResponse(BaseModel):
    message: str
