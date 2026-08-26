"""
Fire-and-forget Allie event capture.

Single source of truth — all WC3 boundary events route through here.
Never raises, never blocks the request cycle.
"""
from __future__ import annotations

import json
import pathlib
import subprocess

_ALLIE_CAPTURE = pathlib.Path.home() / "Allie" / "scripts" / "allie-capture.py"


def allie_capture(event: str, message: str = "", data: dict | None = None):
    """Send an event to Allie's capture script. Fire-and-forget."""
    if not _ALLIE_CAPTURE.exists():
        return
    try:
        args = [
            "python3", str(_ALLIE_CAPTURE),
            "--source", "WC3",
            "--event", event,
            "--message", message[:200],
        ]
        if data:
            args += ["--data", json.dumps(data)]
        subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass
