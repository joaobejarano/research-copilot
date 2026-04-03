import json
from pathlib import Path

from evals.runner import (
    load_dataset,
    run_eval_dataset,
    write_json_report,
    write_markdown_report,
)

SEED_DATASET_PATH = Path("evals/datasets/stage7_seed_cases.json")


def test_load_seed_dataset_is_valid() -> None:
    dataset = load_dataset(SEED_DATASET_PATH)

    assert dataset.dataset_id == "stage7_seed_cases"
    assert dataset.version == "2.0.0"
    assert len(dataset.document_fixtures) == 1
    assert len(dataset.cases) == 5


def test_run_eval_dataset_reports_metrics_for_all_cases() -> None:
    dataset = load_dataset(SEED_DATASET_PATH)

    report = run_eval_dataset(dataset)

    assert report.dataset_id == "stage7_seed_cases"
    assert report.summary.total_cases == 5
    assert report.summary.passed_cases == 5
    assert report.summary.failed_cases == 0

    required_metric_keys = {
        "schema_adherence",
        "abstention_correctness",
        "citation_presence",
        "citation_accuracy",
    }
    for result in report.results:
        assert result.pass_fail == "pass"
        assert required_metric_keys.issubset(result.metrics.keys())
        assert result.http_status_code == 200


def test_run_eval_dataset_fails_when_expected_status_is_wrong() -> None:
    dataset = load_dataset(SEED_DATASET_PATH)

    first_case = dataset.cases[0].model_copy(update={"expected_status": "insufficient_evidence"})
    modified_dataset = dataset.model_copy(update={"cases": [first_case, *dataset.cases[1:]]})

    report = run_eval_dataset(modified_dataset)

    assert report.summary.total_cases == 5
    assert report.summary.failed_cases >= 1
    failing_case = next(result for result in report.results if result.case_id == first_case.id)
    assert failing_case.pass_fail == "fail"
    assert failing_case.metrics["expected_status_match"] == 0.0


def test_write_reports_create_json_and_markdown_outputs(tmp_path: Path) -> None:
    dataset = load_dataset(SEED_DATASET_PATH)
    report = run_eval_dataset(dataset)

    json_path = tmp_path / "eval_report.json"
    markdown_path = tmp_path / "eval_report.md"

    write_json_report(report, json_path)
    write_markdown_report(report, markdown_path)

    json_payload = json.loads(json_path.read_text(encoding="utf-8"))
    markdown_payload = markdown_path.read_text(encoding="utf-8")

    assert json_payload["dataset_id"] == "stage7_seed_cases"
    assert json_payload["summary"]["total_cases"] == 5
    assert len(json_payload["results"]) == 5
    assert "# Eval Report" in markdown_payload
    assert "| case_id | workflow | status | http |" in markdown_payload
