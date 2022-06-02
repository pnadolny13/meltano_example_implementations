import json
import os

import yaml


def read_dbt_manifest():
    local_filepath = f"/Users/pnadolny/Documents/Git/GitHub/pnadolny/meltano_example_implementations/meltano_projects/end_to_end_demo/.meltano/transformers/dbt/target/manifest.json"
    with open(local_filepath) as f:
        return json.load(f)


dbt_nodes = read_dbt_manifest()

selected_tables = json.loads(os.getenv("SUPERSET_TABLES", os.getenv("SUPERSET_DOCKER_TABLES", "[]")))

tables = []
if os.getenv("SUPERSET_SYNC_ASSETS"):
    for table_name, table_def in dbt_nodes.get("nodes").items():
        if (
            selected_tables and
            table_name not in selected_tables
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
        "database_name": os.getenv("SUPERSET_DATABASE_NAME", os.getenv("SUPERSET_DOCKER_DATABASE_NAME", "db_name")),
        "extra": '{"allows_virtual_table_explore":true,"metadata_params":{},"engine_params":{},"schemas_allowed_for_csv_upload":[]}',
        "sqlalchemy_uri": os.getenv("SUPERSET_SQLALCHEMY_URI", os.getenv("SUPERSET_DOCKER_SQLALCHEMY_URI")),
        "tables": tables
    }
    superset_data = {
        "databases": [
            database_def
        ]
    }

    with open("/Users/pnadolny/Documents/Git/GitHub/pnadolny/meltano_example_implementations/meltano_projects/end_to_end_demo/.meltano/run/superset/datasources.yml", "w") as yaml_file:
        yaml.dump(superset_data, yaml_file, default_flow_style=False)

with open("/Users/pnadolny/Documents/Git/GitHub/pnadolny/meltano_example_implementations/meltano_projects/end_to_end_demo/.meltano/run/superset/requirements-local.txt", "w") as req_file:
    deps = "\n".join(json.loads(os.getenv("SUPERSET_ADDITIONAL_DEPENDENCIES", os.getenv("SUPERSET_DOCKER_ADDITIONAL_DEPENDENCIES", "[]"))))
    content = f"# Add database driver dependencies here https://superset.apache.org/docs/databases/installing-database-drivers\n{deps}"
    req_file.write(content)