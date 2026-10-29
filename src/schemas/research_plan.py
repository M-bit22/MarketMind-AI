
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    """Reject unknown fields and validate input types strictly."""
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )


class ResearchQuestion(StrictModel):
    question_id: str = Field(
        pattern=r"^Q[1-9][0-9]*$",
        description="Unique question ID, such as Q1 or Q2.",
    )
    question: str = Field(min_length=10, max_length=500)
    purpose: str = Field(min_length=5, max_length=300)
    search_queries: list[str] = Field(min_length=1, max_length=5)
    priority: Literal["high", "medium", "low"]


class ResearchPlan(StrictModel):
    research_topic: str = Field(min_length=5, max_length=300)
    research_objective: str = Field(min_length=10, max_length=1000)
    scope_included: list[str] = Field(min_length=1, max_length=10)
    scope_excluded: list[str] = Field(max_length=10)
    sub_questions: list[ResearchQuestion] = Field(
        min_length=2,
        max_length=8,
    )
    completion_criteria: list[str] = Field(
        min_length=1,
        max_length=8,
    )

    @model_validator(mode="after")
    def validate_question_ids(self):
        ids = [question.question_id for question in self.sub_questions]
        if len(ids) != len(set(ids)):
            raise ValueError("question_id values must be unique")
        return self
