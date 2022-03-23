# This file is managed by the 'airflow' file bundle and updated automatically when `meltano upgrade` is run.
# To prevent any manual changes from being overwritten, remove the file bundle from `meltano.yml` or disable automatic updates:
#     meltano config --plugin-type=files airflow set _update orchestrate/dags/meltano.py false

from datetime import timedelta
import os
import logging
import yaml
from generators.generator_factory import GeneratorFactory
from generator_cache_builder import GeneratorCacheBuilder

logger = logging.getLogger(__name__)
project_root = os.getenv("MELTANO_PROJECT_ROOT", os.getcwd())

# TODO: how can we get this from the environment or somewhere else?
MELTANO_ENVIRONMENT = "dev"

DEFAULT_ARGS = {
    "owner": "meltano",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "catchup": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
    "concurrency": 1,
}

DEFAULT_TAGS = ["meltano"]

args = DEFAULT_ARGS.copy()

# Read all dag defintions
with open(os.path.join(project_root, "orchestrate", "dag_definition.yml"), "r") as yaml_file:
    yaml_content = yaml.safe_load(yaml_file)
    dags_all = yaml_content.get("dags", {})
    generator_configs = dags_all.get("generator_configs")
    dags = dags_all.get("dag_definitions")

# Add all Meltano schedules to list of dag defintions
# TODO: in the future these should be co-located in the dag definition file
file_name = os.path.join(project_root, "orchestrate", "generator_cache.yml")
if not os.path.isfile(file_name):
    logger.info(f"Generator cache not found, rebuilding..")
    builder = GeneratorCacheBuilder()
    builder.refresh_cache()
    logger.info(f"Generator cache rebuild complete.")

with open(file_name, "r") as yaml_file:
    yaml_content = yaml.safe_load(yaml_file)
    for schedule in yaml_content.get("meltano_schedules", []):
        dags[f"meltano_{schedule['name']}"] = {**schedule, "generator": "meltano_schedules"}


# Iterate all dag defintions and register them with Airflow
for dag_name, dag_def in dags.items():
    logger.info(f"Considering dag '{dag_name}' - {dag_def}")
    dag_id = f"meltano_{dag_name}"

    generator_obj = GeneratorFactory.get_generator(dag_def["generator"])
    generator = generator_obj(project_root, MELTANO_ENVIRONMENT, generator_configs)
    dag = generator.create_dag(dag_name, dag_def, args)
    for tasks in generator.create_tasks(dag, dag_name, dag_def):
        if len(tasks) > 1:
            tasks[0] >> tasks[1]

    # register the dag
    globals()[dag_id] = dag

    logger.info(f"DAG created for schedule '{dag_id}'")
