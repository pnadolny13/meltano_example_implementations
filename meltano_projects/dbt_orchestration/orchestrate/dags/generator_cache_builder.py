import os
import yaml
import subprocess
import json
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class GeneratorCacheBuilder:

    def __init__(self):
        self.project_root = os.getenv("MELTANO_PROJECT_ROOT", os.getcwd())
        self.meltano_bin = ".meltano/run/bin"

        if not Path(self.project_root).joinpath(self.meltano_bin).exists():
            logger.warning(
                f"A symlink to the 'meltano' executable could not be found at '{self.meltano_bin}'. Falling back on expecting it to be in the PATH instead."
            )
            self.meltano_bin = "meltano"

    def read_dag_definitions(self):
        with open(os.path.join(self.project_root, "orchestrate", "dag_definition.yml"), "r") as yaml_file:
            yaml_content = yaml.safe_load(yaml_file)
            return yaml_content.get("dags", {}).get("dag_definitions")

    def read_dbt_manifest(self):
        local_filepath = f"{self.project_root}/.meltano/transformers/dbt/target/manifest.json"
        with open(local_filepath) as f:
            return json.load(f)

    def get_models_from_select(self, project_root, env, select_criteria):
        logger.info(f"Running dbt ls for {select_criteria}")
        output = subprocess.run(
            f"{self.meltano_bin} --environment={env} invoke dbt ls --select {select_criteria}".split(" "),
            cwd=project_root,
            check=True,
            capture_output=True,
        )
        return output.stdout.decode("utf-8").split("\n")

    def create_dbt_selection_cache(self):
        selections = {}
        dags = self.read_dag_definitions()
        for dag_name, dag_def in dags.items():
            selection =  self.get_models_from_select(
                self.project_root,
                'dev',
                dag_def["selection_rule"]
            )
            selection.remove("")
            selections[dag_name] = selection
        return selections

    def create_meltano_schedule_cache(self):
        # Add Meltano schedules to cache
        logger.info(f"Running Meltano schedule list..")
        result = subprocess.run(
            [self.meltano_bin, "schedule", "list", "--format=json"],
            cwd=self.project_root,
            stdout=subprocess.PIPE,
            universal_newlines=True,
            check=True,
        )
        return json.loads(result.stdout)

    def write_cache(self, dbt_selections, dbt_manifest, meltano_schedules):
        cache = {
            "selections": dbt_selections,
            "manifest": dbt_manifest,
            "meltano_schedules": meltano_schedules,
        }
        with open(os.path.join(self.project_root, "orchestrate", "generator_cache.yml"), "w") as yaml_file:
            yaml.dump(cache, yaml_file, default_flow_style=False)

    def refresh_cache(self):
        dbt_selections = self.create_dbt_selection_cache()
        dbt_manifest = self.read_dbt_manifest()
        meltano_schedules = self.create_meltano_schedule_cache()
        self.write_cache(dbt_selections, dbt_manifest, meltano_schedules)

if __name__ == "__main__":
    builder = GeneratorCacheBuilder()
    builder.refresh_cache()
