import logging
from datetime import timedelta
from generators.base_generator import BaseGenerator
from airflow import DAG
try:
    from airflow.operators.bash_operator import BashOperator
except ImportError:
    from airflow.operators.bash import BashOperator


logger = logging.getLogger(__name__)


class MeltanoScheduleGenerator(BaseGenerator):

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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def create_tasks(self, dag, dag_name, dag_def):
        yield [
            BashOperator(
                task_id="extract_load",
                bash_command=f"cd {self.project_root}; {self.meltano_bin} schedule run {dag_def['name']}",
                dag=dag,
            )
        ]

    def create_dag(self, dag_name: str, dag_def: dict, args: dict) -> DAG:
        logger.info(f"Considering schedule '{dag_def['name']}': {dag_def}")

        if not dag_def["cron_interval"]:
            logger.info(
                f"No DAG created for schedule '{dag_def['name']}' because its interval is set to `@once`."
            )
            # TODO: handle this better
            return

        if dag_def["start_date"]:
            args["start_date"] = dag_def["start_date"]

        dag_id = f"meltano_{dag_def['name']}"

        tags = ["meltano"]
        if dag_def["extractor"]:
            tags.append(dag_def["extractor"])
        if dag_def["loader"]:
            tags.append(dag_def["loader"])
        if dag_def["transform"] == "run":
            tags.append("transform")
        elif dag_def["transform"] == "only":
            tags.append("transform-only")

        return DAG(
            dag_id,
            tags=tags,
            catchup=False,
            default_args=args,
            schedule_interval=dag_def["interval"],
            max_active_runs=1,
        )