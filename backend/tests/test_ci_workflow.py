from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


@pytest.mark.fast
def test_ci_workflow_contains_expected_smoke_and_matrix():
    """Sanity check the CI workflow to catch accidental regressions.

    - Smoke step should include a non-blocking run (e.g., `|| true`).
    - Matrix should include Python 3.11/3.12/3.13.
    - Docs layout validation step should exist.
    """
    wf = ROOT / ".github" / "workflows" / "ci.yml"
    if not wf.exists():
        pytest.skip("CI workflow .github/workflows/ci.yml not yet created")
    content = _read(wf)

    # Smoke non-blocking: allow variations in whitespace/newlines
    assert "pytest -q -m smoke" in content
    assert "|| true" in content, "Smoke tests should not block (missing '|| true')"

    # Matrix versions (flexible check)
    flat = content.replace("\n", " ")
    for ver in ("3.11", "3.12", "3.13"):
        assert ver in flat, f"Expected Python {ver} in matrix"

    # Docs layout validation present
    assert "validate_docs_location.sh" in content
