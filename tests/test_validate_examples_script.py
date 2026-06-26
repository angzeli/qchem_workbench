from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_validate_examples_script_exits_zero():
    result = subprocess.run(
        [sys.executable, "scripts/validate_examples.py"],
        cwd=Path(__file__).resolve().parents[1],
        check=False,
        text=True,
        capture_output=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "[v2 example gate] basic molecule workflow" in result.stdout
    assert "v2 example validation gate completed successfully." in result.stdout
