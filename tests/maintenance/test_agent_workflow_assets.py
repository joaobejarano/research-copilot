from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

REQUIRED_SKILL_FILES = [
    ".agents/skills/bootstrap-repo/SKILL.md",
    ".agents/skills/run-local-checks/SKILL.md",
    ".agents/skills/update-readme/SKILL.md",
    ".agents/skills/implementation-strategy/SKILL.md",
    ".agents/skills/eval-runner/SKILL.md",
    ".agents/skills/prompt-regression-check/SKILL.md",
    ".agents/skills/docs-sync/SKILL.md",
    ".agents/skills/pr-draft-summary/SKILL.md",
]

REQUIRED_AGENT_WORKFLOW_DOCS = [
    "docs/agent-development-workflow.md",
]


def _assert_existing_file(relative_path: str) -> None:
    path = REPO_ROOT / relative_path
    assert path.exists(), f"Missing required file: {relative_path}"
    assert path.is_file(), f"Expected file, found non-file path: {relative_path}"


def test_agents_md_exists() -> None:
    _assert_existing_file("AGENTS.md")


def test_required_skill_files_exist() -> None:
    for relative_path in REQUIRED_SKILL_FILES:
        _assert_existing_file(relative_path)


def test_agent_workflow_docs_exist() -> None:
    for relative_path in REQUIRED_AGENT_WORKFLOW_DOCS:
        _assert_existing_file(relative_path)
