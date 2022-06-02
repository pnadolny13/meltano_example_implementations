# This file is managed by the 'airflow' file bundle and updated automatically when `meltano upgrade` is run.
# To prevent any manual changes from being overwritten, remove the file bundle from `meltano.yml` or disable automatic updates:
#     meltano config --plugin-type=files airflow set _update orchestrate/dags/meltano.py false

# If you want to define a custom DAG, create
# a new file under orchestrate/dags/ and Airflow
# will pick it up automatically.

import os
import logging
import subprocess
import json

from airflow import DAG
try:
    from airflow.operators.bash_operator import BashOperator
except ImportError:
    from airflow.operators.bash import BashOperator

from datetime import timedelta
from pathlib import Path


logger = logging.getLogger(__name__)


DEFAULT_ARGS = {
    "owner": "airflow",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "catchup": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
    "concurrency": 1,
}

DEFAULT_TAGS = ["meltano"]

project_root = os.getenv("MELTANO_PROJECT_ROOT", os.getcwd())

meltano_bin = ".meltano/run/bin"

if not Path(project_root).joinpath(meltano_bin).exists():
    logger.warning(
        f"A symlink to the 'meltano' executable could not be found at '{meltano_bin}'. Falling back on expecting it to be in the PATH instead."
    )
    meltano_bin = "meltano"


result = subprocess.run(
    [meltano_bin, "schedule", "list", "--format=json"],
    cwd=project_root,
    stdout=subprocess.PIPE,
    universal_newlines=True,
    check=True,
)
schedules = json.loads(result.stdout)

for schedule in schedules:
    logger.info(f"Considering schedule '{schedule['name']}': {schedule}")

    if not schedule["cron_interval"]:
        logger.info(
            f"No DAG created for schedule '{schedule['name']}' because its interval is set to `@once`."
        )
        continue

    args = DEFAULT_ARGS.copy()
    if schedule["start_date"]:
        args["start_date"] = schedule["start_date"]

    dag_id = f"meltano_{schedule['name']}"

    tags = DEFAULT_TAGS.copy()
    if schedule["extractor"]:
        tags.append(schedule["extractor"])
    if schedule["loader"]:
        tags.append(schedule["loader"])
    if schedule["transform"] == "run":
        tags.append("transform")
    elif schedule["transform"] == "only":
        tags.append("transform-only")

    # from https://airflow.apache.org/docs/stable/scheduler.html#backfill-and-catchup
    #
    # It is crucial to set `catchup` to False so that Airflow only create a single job
    # at the tail end of date window we want to extract data.
    #
    # Because our extractors do not support date-window extraction, it serves no
    # purpose to enqueue date-chunked jobs for complete extraction window.
    dag = DAG(
        dag_id,
        tags=tags,
        catchup=False,
        default_args=args,
        schedule_interval=schedule["interval"],
        max_active_runs=1,
    )

    elt = BashOperator(
        task_id="extract_load",
        bash_command=f"cd {project_root}; {meltano_bin} schedule run {schedule['name']}",
        dag=dag,
    )

    # register the dag
    globals()[dag_id] = dag

    logger.info(f"DAG created for schedule '{schedule['name']}'")
