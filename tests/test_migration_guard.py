import os
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.fast
def test_migration_guard_runs_without_failure():
    """Run the migration guard script in warn-only mode so local dev and PR branches don't fail tests.

    We set ALLOW_MULTIPLE_MIGRATIONS=1 to ensure the script exits 0 regardless of branch,
    while still exercising the script path.
    """
    script = ROOT / ".github" / "scripts" / "check_single_migration.sh"
    assert script.exists(), f"Missing script: {script}"

    env = os.environ.copy()
    env["ALLOW_MULTIPLE_MIGRATIONS"] = "1"
    # Ensure bash is used and cwd is repo root
    proc = subprocess.run(["bash", str(script)], cwd=str(ROOT), env=env)
    assert proc.returncode == 0, "Migration guard script failed unexpectedly."
