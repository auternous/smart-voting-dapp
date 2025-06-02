from pydantic import BaseModel, Field, field_validator
from typing import List

class CreatePoll(BaseModel):
    question: str = Field(..., min_length=1)
    options: List[str]
    duration: int = Field(..., gt=0)

    @field_validator("options")
    @classmethod
    def validate_options(cls, v):
        if len(v) < 2:
            raise ValueError("At least two options required")
        return v

class RelayVoteRequest(BaseModel):
    poll_id: int
    option_id: int
    voter: str
    signature: str