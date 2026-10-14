
from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, model_validator

from app.schemas.analysis import GeminiAnalysisOutput


class AnalysisApiStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class AnalysisApiResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    analysis_id: UUID
    submission_id: UUID
    status: AnalysisApiStatus
    result: GeminiAnalysisOutput | None = None
    failure_code: str | None = None
    created_at: datetime
    completed_at: datetime | None = None

    @model_validator(mode="after")
    def validate_status(self):
        if self.status == AnalysisApiStatus.COMPLETED:
            if self.result is None or self.completed_at is None:
                raise ValueError(
                    "Completed analysis requires result and timestamp."
                )

        return self


class AnalysisErrorResponse(BaseModel):
    error: str
    message: str
