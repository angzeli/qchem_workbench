"""Scheduler script templates for Gaussian jobs."""

from __future__ import annotations

from pathlib import Path


SCHEDULER_NAMES = ("shell", "slurm", "pbs")
TEMPLATE_NOTICE = (
    "Template only: review and adapt commands, resources, modules, and queues "
    "for the local system before use."
)


def render_gaussian_scheduler_script(scheduler: str, input_filename: str) -> str:
    """Return a Gaussian job script template without executing anything."""

    if scheduler not in SCHEDULER_NAMES:
        raise ValueError(f"unsupported scheduler template {scheduler!r}")

    output_filename = f"{Path(input_filename).stem}.log"
    job_name = Path(input_filename).stem
    if scheduler == "shell":
        return _shell_template(input_filename, output_filename)
    if scheduler == "slurm":
        return _slurm_template(job_name, input_filename, output_filename)
    return _pbs_template(job_name, input_filename, output_filename)


def _shell_template(input_filename: str, output_filename: str) -> str:
    return (
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        f"# {TEMPLATE_NOTICE}\n"
        "\n"
        'GAUSSIAN_CMD="${GAUSSIAN_CMD:-g16}"\n'
        f'"$GAUSSIAN_CMD" < "{input_filename}" > "{output_filename}"\n'
    )


def _slurm_template(job_name: str, input_filename: str, output_filename: str) -> str:
    return (
        "#!/usr/bin/env bash\n"
        f"#SBATCH --job-name={job_name}\n"
        f"#SBATCH --output={job_name}.slurm.out\n"
        "#SBATCH --cpus-per-task=1\n"
        "#SBATCH --mem=4G\n"
        "#SBATCH --time=01:00:00\n"
        f"# {TEMPLATE_NOTICE}\n"
        "\n"
        "set -euo pipefail\n"
        'GAUSSIAN_CMD="${GAUSSIAN_CMD:-g16}"\n'
        f'"$GAUSSIAN_CMD" < "{input_filename}" > "{output_filename}"\n'
    )


def _pbs_template(job_name: str, input_filename: str, output_filename: str) -> str:
    return (
        "#!/usr/bin/env bash\n"
        f"#PBS -N {job_name}\n"
        f"#PBS -o {job_name}.pbs.out\n"
        "#PBS -l select=1:ncpus=1:mem=4gb\n"
        "#PBS -l walltime=01:00:00\n"
        f"# {TEMPLATE_NOTICE}\n"
        "\n"
        "set -euo pipefail\n"
        'GAUSSIAN_CMD="${GAUSSIAN_CMD:-g16}"\n'
        f'"$GAUSSIAN_CMD" < "{input_filename}" > "{output_filename}"\n'
    )
