from __future__ import annotations

import pytest

from qchem_workbench.backends.gaussian_scheduler import (
    render_gaussian_scheduler_script,
)


def test_shell_scheduler_template_marks_local_adaptation():
    script = render_gaussian_scheduler_script("shell", "water.gjf")

    assert "Template only" in script
    assert 'GAUSSIAN_CMD="${GAUSSIAN_CMD:-g16}"' in script
    assert '"$GAUSSIAN_CMD" < "water.gjf" > "water.log"' in script


def test_slurm_scheduler_template_contains_generic_directives():
    script = render_gaussian_scheduler_script("slurm", "water.gjf")

    assert "#SBATCH --job-name=water" in script
    assert "#SBATCH --cpus-per-task=1" in script
    assert "#SBATCH --mem=4G" in script
    assert "Template only" in script
    assert '"$GAUSSIAN_CMD" < "water.gjf" > "water.log"' in script


def test_pbs_scheduler_template_contains_generic_directives():
    script = render_gaussian_scheduler_script("pbs", "water.gjf")

    assert "#PBS -N water" in script
    assert "#PBS -l select=1:ncpus=1:mem=4gb" in script
    assert "#PBS -l walltime=01:00:00" in script
    assert "Template only" in script


def test_unknown_scheduler_template_is_error():
    with pytest.raises(ValueError, match="unsupported scheduler"):
        render_gaussian_scheduler_script("local-cluster", "water.gjf")
