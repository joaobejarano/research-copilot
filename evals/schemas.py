from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

SCHEMA_CONFIG = ConfigDict(extra="forbid", str_strip_whitespace=True)

WorkflowType = Literal[
    "grounded_qa",
    "memo_generation",
    "kpi_extraction",
    "risk_extraction",
    "timeline_building",
]
PassFail = Literal["pass", "fail"]


class EvalDocumentReference(BaseModel):
    reference_id: str = Field(min_length=1, max_length=120)
    document_id: int | None = Field(default=None, ge=1)
    source_filename: str | None = Field(default=None, max_length=260)
    notes: str | None = Field(default=None, max_length=600)

    model_config = SCHEMA_CONFIG


class EvalCase(BaseModel):
    id: str = Field(min_length=1, max_length=120)
    workflow_type: WorkflowType
    document_reference: EvalDocumentReference
    input: dict[str, Any] = Field(default_factory=dict)
    expected_behavior: str = Field(min_length=1, max_length=1200)
    expected_fields: list[str] | None = Field(default=None, max_length=80)
    expected_status: str | None = Field(default=None, min_length=1, max_length=120)

    model_config = SCHEMA_CONFIG

    @model_validator(mode="after")
    def validate_input_not_empty(self) -> "EvalCase":
        if not self.input:
            raise ValueError("input must include at least one field.")
        return self


class EvalDataset(BaseModel):
    dataset_id: str = Field(min_length=1, max_length=120)
    version: str = Field(min_length=1, max_length=40)
    description: str = Field(min_length=1, max_length=1200)
    cases: list[EvalCase] = Field(min_length=1, max_length=1000)

    model_config = SCHEMA_CONFIG

    @model_validator(mode="after")
    def validate_unique_case_ids(self) -> "EvalDataset":
        seen: set[str] = set()
        duplicates: list[str] = []
        for case in self.cases:
            if case.id in seen:
                duplicates.append(case.id)
            seen.add(case.id)
        if duplicates:
            duplicate_list = ", ".join(sorted(set(duplicates)))
            raise ValueError(f"case ids must be unique. duplicates: {duplicate_list}")
        return self


class EvalResult(BaseModel):
    case_id: str = Field(min_length=1, max_length=120)
    workflow_type: WorkflowType
    pass_fail: PassFail
    metrics: dict[str, float] = Field(default_factory=dict)
    notes: list[str] = Field(default_factory=list, max_length=80)

    model_config = SCHEMA_CONFIG


class EvalRunSummary(BaseModel):
    total_cases: int = Field(ge=0)
    passed_cases: int = Field(ge=0)
    failed_cases: int = Field(ge=0)

    model_config = SCHEMA_CONFIG


class EvalRunReport(BaseModel):
    run_id: str = Field(min_length=1, max_length=120)
    generated_at: datetime
    dataset_id: str = Field(min_length=1, max_length=120)
    dataset_version: str = Field(min_length=1, max_length=40)
    results: list[EvalResult] = Field(default_factory=list, max_length=2000)
    summary: EvalRunSummary

    model_config = SCHEMA_CONFIG

    @staticmethod
    def utc_now() -> datetime:
        return datetime.now(timezone.utc)
