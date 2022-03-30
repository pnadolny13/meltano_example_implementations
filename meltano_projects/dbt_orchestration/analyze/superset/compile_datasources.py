import os
import yaml
import subprocess
import json

ENVIRONMENT = "dev"

def read_dbt_manifest(project_root):
    local_filepath = f"{project_root}/.meltano/transformers/dbt/target/manifest.json"
    with open(local_filepath) as f:
        return json.load(f)

project_root = os.getenv("MELTANO_PROJECT_ROOT", os.getcwd())
meltano_bin = ".meltano/run/bin"
result = subprocess.run(
    [meltano_bin, f"--environment={ENVIRONMENT}","config", "superset"],
    cwd=project_root,
    stdout=subprocess.PIPE,
    universal_newlines=True,
    check=True,
)
superset_config = json.loads(result.stdout)

dbt_nodes = read_dbt_manifest(project_root)

tables = []
for table_name, table_def in dbt_nodes.get("nodes").items():
    if (
        not superset_config.get("load_all_dbt_models") and
        table_name not in superset_config.get("tables")
    ):
        continue
    super_table_def = {}
    table_alias = table_def.get("alias")
    t_description = table_def.get("description")
    cols = table_def.get("columns")
    super_cols = []
    for col_name, col_def in cols.items():
        super_cols.append(
            {
                "column_name": col_def.get("name"),
                "type": col_def.get("data_type") or "VARCHAR",
                "description": col_def.get("description")
            }
        )
    super_table_def["table_name"] = table_alias
    super_table_def["columns"] = super_cols
    super_table_def["schema"] = table_def.get("schema")
    tables.append(super_table_def)


database_def = {
    "database_name": "local_postgres",
    "extra": '{"allows_virtual_table_explore":true,"metadata_params":{},"engine_params":{},"schemas_allowed_for_csv_upload":[]}',
    "sqlalchemy_uri": "postgresql+psycopg2://meltano:meltano@host.docker.internal:5432/warehouse",
    "tables": tables
}
superset_data = {
    "databases": [
        database_def
    ]
}

with open(os.path.join(project_root, "analyze", "superset", "assets", "database", "datasources.yml"), "w") as yaml_file:
    yaml.dump(superset_data, yaml_file, default_flow_style=False)
