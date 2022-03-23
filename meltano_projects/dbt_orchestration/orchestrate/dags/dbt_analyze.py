import os
import yaml
import subprocess
import json
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class DbtAnalyze:

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

    @staticmethod
    def _get_full_model_name(manifest, node):
        if manifest["nodes"].get(node):
            node_details = manifest["nodes"][node]
            path_sql = node_details["path"].replace("/", ".")
            path = path_sql.replace(".sql", "")
            package_name = node_details["package_name"]
            return f"{package_name}.{path}"
        else:
            return node

    @staticmethod
    def get_selection_set(dbt_selections):
        unique_selects = set()
        for _, selections in dbt_selections.items():
            for selection in selections:
                unique_selects.add(selection)
        return unique_selects

    def get_all_dbt_set(self, dbt_manifest):
        unique_nodes = set()
        for node in dbt_manifest.get("nodes"):
            if node.split(".")[0] == "model":
                full_name = self._get_full_model_name(dbt_manifest, node)
                unique_nodes.add(full_name)
        return unique_nodes

    def find_missing_models(self, dbt_manifest, dbt_selections):
        selects_set = self.get_selection_set(dbt_selections)
        all_nodes_set = self.get_all_dbt_set(dbt_manifest)
        return all_nodes_set - selects_set

    def analyze(self):
        dbt_manifest = self.read_dbt_manifest()
        dbt_selections = self.create_dbt_selection_cache()
        return self.find_missing_models(dbt_manifest, dbt_selections)

if __name__ == "__main__":
    analyze = DbtAnalyze()
    missing_models = analyze.analyze()
    if missing_models:
        print("Models not referenced:")
        for model in missing_models:
            print(f"    {model}")
    else:
        print("All models referenced in selection criteria!")
