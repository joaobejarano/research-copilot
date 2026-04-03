from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from evals.schemas import EvalCase, EvalDataset, EvalResult, EvalRunReport, EvalRunSummary

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_DATASET_PATH = BASE_DIR / "datasets" / "stage7_seed_cases.json"
DEFAULT_RESULTS_DIR = BASE_DIR / "results"

REQUIRED_INPUT_KEYS: dict[str, set[str]] = {
    "grounded_qa": {"question"},
    "memo_generation": {"instruction"},
    "kpi_extraction": {"instruction"},
    "risk_extraction": {"instruction"},
    "timeline_building": {"instruction"},
}

ALLOWED_STATUSES: dict[str, set[str]] = {
    "grounded_qa": {"answered", "insufficient_evidence"},
    "memo_generation": {"generated", "insufficient_evidence"},
    "kpi_extraction": {"completed", "insufficient_evidence"},
    "risk_extraction": {"completed", "insufficient_evidence"},
    "timeline_building": {"completed", "insufficient_evidence"},
}

ALLOWED_EXPECTED_FIELDS: dict[str, set[str]] = {
    "grounded_qa": {
        "question",
        "answer",
        "status",
        "citations",
        "verification",
        "confidence",
        "gate_decision",
        "issues",
    },
    "memo_generation": {"workflow", "document_id", "status", "memo", "evidence"},
    "kpi_extraction": {"workflow", "document_id", "status", "kpis", "evidence"},
    "risk_extraction": {"workflow", "document_id", "status", "risks", "evidence"},
    "timeline_building": {"workflow", "document_id", "status", "events", "evidence"},
}


def _normalize_string(value: Any) -> str:
    return str(value).strip()


def load_dataset(dataset_path: Path) -> EvalDataset:
    payload = json.loads(dataset_path.read_text(encoding="utf-8"))
    return EvalDataset.model_validate(payload)


def evaluate_case(case: EvalCase) -> EvalResult:
    notes: list[str] = []
    metric_scores: list[float] = []

    required_keys = REQUIRED_INPUT_KEYS[case.workflow_type]
    missing_keys: list[str] = []
    for key in sorted(required_keys):
        if key not in case.input:
            missing_keys.append(key)
            continue
        normalized_value = _normalize_string(case.input[key])
        if not normalized_value:
            missing_keys.append(key)

    has_required_inputs = not missing_keys
    metric_scores.append(1.0 if has_required_inputs else 0.0)
    if not has_required_inputs:
        notes.append(
            "Missing required input keys: " + ", ".join(missing_keys)
        )

    status_is_valid = True
    if case.expected_status is not None:
        status_is_valid = case.expected_status in ALLOWED_STATUSES[case.workflow_type]
        if not status_is_valid:
            allowed_statuses = ", ".join(sorted(ALLOWED_STATUSES[case.workflow_type]))
            notes.append(
                "Invalid expected_status for workflow "
                f"'{case.workflow_type}': '{case.expected_status}'. "
                f"Allowed: {allowed_statuses}."
            )
    metric_scores.append(1.0 if status_is_valid else 0.0)

    fields_are_valid = True
    if case.expected_fields is not None:
        allowed_fields = ALLOWED_EXPECTED_FIELDS[case.workflow_type]
        invalid_fields = [
            field_name for field_name in case.expected_fields if field_name not in allowed_fields
        ]
        fields_are_valid = not invalid_fields
        if not fields_are_valid:
            notes.append(
                "Invalid expected_fields for workflow "
                f"'{case.workflow_type}': {', '.join(invalid_fields)}."
            )
    metric_scores.append(1.0 if fields_are_valid else 0.0)

    overall_score = sum(metric_scores) / len(metric_scores)
    pass_fail = "pass" if overall_score == 1.0 else "fail"

    return EvalResult(
        case_id=case.id,
        workflow_type=case.workflow_type,
        pass_fail=pass_fail,
        metrics={
            "required_inputs_present": 1.0 if has_required_inputs else 0.0,
            "expected_status_valid": 1.0 if status_is_valid else 0.0,
            "expected_fields_valid": 1.0 if fields_are_valid else 0.0,
            "overall_score": round(overall_score, 6),
        },
        notes=notes,
    )


def run_eval_dataset(dataset: EvalDataset) -> EvalRunReport:
    results = [evaluate_case(case) for case in dataset.cases]
    passed_cases = sum(1 for result in results if result.pass_fail == "pass")
    failed_cases = len(results) - passed_cases

    now = datetime.now(timezone.utc)
    run_id = now.strftime("stage7-local-%Y%m%dT%H%M%SZ")

    return EvalRunReport(
        run_id=run_id,
        generated_at=now,
        dataset_id=dataset.dataset_id,
        dataset_version=dataset.version,
        results=results,
        summary=EvalRunSummary(
            total_cases=len(results),
            passed_cases=passed_cases,
            failed_cases=failed_cases,
        ),
    )


def write_report(report: EvalRunReport, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report.model_dump(mode="json"), indent=2) + "\n",
        encoding="utf-8",
    )


def build_output_path(output_arg: str | None) -> Path:
    if output_arg:
        return Path(output_arg)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return DEFAULT_RESULTS_DIR / f"stage7_eval_report_{timestamp}.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run local Stage 7 evaluation foundation checks for grounded workflows."
    )
    parser.add_argument(
        "--dataset",
        default=str(DEFAULT_DATASET_PATH),
        help="Path to eval dataset JSON file.",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Optional output report path. Defaults to evals/results/<timestamp>.json",
    )
    parser.add_argument(
        "--fail-on-fail",
        action="store_true",
        help="Return exit code 1 if any case fails.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    dataset_path = Path(args.dataset)

    try:
        dataset = load_dataset(dataset_path)
    except FileNotFoundError:
        print(f"Dataset not found: {dataset_path}")
        return 2
    except json.JSONDecodeError as exc:
        print(f"Dataset JSON parsing failed: {exc}")
        return 2
    except ValidationError as exc:
        print("Dataset validation failed:")
        print(exc)
        return 2

    report = run_eval_dataset(dataset)
    output_path = build_output_path(args.output)
    write_report(report, output_path)

    print(f"Loaded dataset: {dataset_path}")
    print(f"Cases: {report.summary.total_cases}")
    print(f"Passed: {report.summary.passed_cases}")
    print(f"Failed: {report.summary.failed_cases}")
    print(f"Report: {output_path}")

    if report.summary.failed_cases > 0:
        print("Failed cases:")
        for result in report.results:
            if result.pass_fail == "pass":
                continue
            details = " | ".join(result.notes) if result.notes else "No details."
            print(f"- {result.case_id}: {details}")

    if args.fail_on_fail and report.summary.failed_cases > 0:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
