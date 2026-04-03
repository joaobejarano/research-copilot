import json
from pathlib import Path

from evals.runner import evaluate_case, load_dataset, run_eval_dataset, write_report
from evals.schemas import EvalCase, EvalDocumentReference

SEED_DATASET_PATH = Path("evals/datasets/stage7_seed_cases.json")


def test_load_seed_dataset_is_valid() -> None:
    dataset = load_dataset(SEED_DATASET_PATH)

    assert dataset.dataset_id == "stage7_seed_cases"
    assert dataset.version == "1.0.0"
    assert len(dataset.cases) == 5


def test_evaluate_case_fails_for_invalid_expected_status() -> None:
    case = EvalCase(
        id="qa_invalid_status",
        workflow_type="grounded_qa",
        document_reference=EvalDocumentReference(reference_id="doc-1"),
        input={"question": "What happened to revenue?"},
        expected_behavior="Should return grounded answer or insufficient evidence.",
        expected_fields=["question", "answer", "status", "citations"],
        expected_status="generated",
    )

    result = evaluate_case(case)

    assert result.pass_fail == "fail"
    assert result.metrics["expected_status_valid"] == 0.0
    assert any("Invalid expected_status" in note for note in result.notes)


def test_run_eval_dataset_reports_all_seed_cases_as_pass() -> None:
    dataset = load_dataset(SEED_DATASET_PATH)

    report = run_eval_dataset(dataset)

    assert report.dataset_id == "stage7_seed_cases"
    assert report.summary.total_cases == 5
    assert report.summary.passed_cases == 5
    assert report.summary.failed_cases == 0
    assert all(result.pass_fail == "pass" for result in report.results)


def test_write_report_creates_json_output(tmp_path: Path) -> None:
    dataset = load_dataset(SEED_DATASET_PATH)
    report = run_eval_dataset(dataset)
    output_path = tmp_path / "eval_report.json"

    write_report(report, output_path)

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["dataset_id"] == "stage7_seed_cases"
    assert payload["summary"]["total_cases"] == 5
    assert len(payload["results"]) == 5
