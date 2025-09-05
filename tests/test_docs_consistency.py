import os
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.fast
def test_docs_consistency_script_succeeds():
    """Runs Scripts/check_docs_consistency.py and expects exit code 0.

    This validates that docs_index.json and readmes TOCs are in-sync.
    """
    script = ROOT / "Scripts" / "check_docs_consistency.py"
    assert script.exists(), f"Missing script: {script}"

    # Ensure we run from repo root so the script's relative paths and git diff work.
    proc = subprocess.run([sys.executable, str(script)], cwd=str(ROOT))
    assert proc.returncode == 0, "Docs consistency check failed. Run Scripts/check_docs_consistency.py locally for details."
