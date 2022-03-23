from abc import ABC, abstractmethod
from airflow import DAG
from pathlib import Path
import logging
from datetime import datetime, timedelta
from airflow.models import Variable
try:
    from airflow.operators.bash_operator import BashOperator
except ImportError:
    from airflow.operators.bash import BashOperator

meltano_log_level = Variable.get("MELTANO_LOG_LEVEL", "info")


logger = logging.getLogger(__name__)

class BaseGenerator(ABC):

    def __init__(self, project_root, env, generator_configs):
        self.project_root = project_root
        self.env = env
        self.generator_configs = generator_configs

        meltano_bin = ".meltano/run/bin"

        if not Path(self.project_root).joinpath(meltano_bin).exists():
            logger.warning(
                f"A symlink to the 'meltano' executable could not be found at '{meltano_bin}'. Falling back on expecting it to be in the PATH instead."
            )
            meltano_bin = "meltano"
        self.meltano_bin = meltano_bin
        self.operator = ""

    @abstractmethod
    def create_tasks(self, dag: DAG, dag_name: str, dag_def: dict):
        pass

    @abstractmethod
    def create_dag(self, dag_name: str, dag_def: dict, args: dict) -> DAG:
        pass

    def get_operator(self, dag, task_id, name, cmd, retry_delay=timedelta(minutes=5), retries=0):
        if self.operator == "k8":
            from meltano_k8_operator import MeltanoKubernetesPodOperator
            task = MeltanoKubernetesPodOperator(
                task_id=task_id,
                name=name,
                environment=self.env,
                log_level=meltano_log_level,
                arguments=[cmd],
                dag=dag,
                retry_delay=retry_delay,
            )
        else:
            task = BashOperator(
                task_id=task_id,
                # name=name,
                bash_command=cmd,
                retries=retries,
                dag=dag,
                retry_delay=retry_delay,
            )
        return task
