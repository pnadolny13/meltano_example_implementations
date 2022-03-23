## DAG Generators

This file bundle comes with DAG generators which translate the configurations from your Meltano project into Airflow DAGs and tasks.

There are currently 2 ways to register DAG to be consumed by the generator:
1. in your Meltano project using the `meltano schedule` command
1. or by defining them directly in the dag_definition.yml file provided by this file bundle.
After installation this file will be in the `orchestrate` directory within your project.

### Option 1: Meltano Schedule Generator

This generator simply schedules your `meltano elt` jobs as a single Airflow task.
If you run a transformation following the EL step, then this will also be encapsulated within the single Airflow task.

To use this generator simply register a schedule in your Meltano project.
Refer to the [create schdule docs](https://docs.meltano.com/reference/command-line-interface#schedule) for more information.

### Option 2: dbt Generator

This generator gives you more fine grain control over your tasks by tapping into dbt's own concept of a DAG.
The generator uses the manifest.json that your dbt project produces along with the Meltano EL streams in order to rebuild the dbt DAG as an Airflow DAG where each model/task is its own Airflow task.
The advantage of this is to allow for model level control and the ability to more precisely rerun certain models.

As part of the DAG definition you can define any dbt selection criteria which allows you to execute your DAG in any way that you'd like but a few common patterns are:

- All - run the entire dbt DAG and all Meltano syncs that feed it.
This approach is useful for small dbt projects.
- Source Based - target a specific dbt source to run which triggers the Meltano EL syncs and all the downstream dbt models connected to that source.
This approach is particularly useful when a source is refreshed infrequently.
- Model Based - target a specific dbt model to refresh which triggers all upstream dbt models along with any connecting Meltano EL jobs that feed them.
This is particularly useful when there are SLA requirements on a particular consumption models like fact and dimension tables feeding a BI tool.

A sample of a DAG that runs the entire dbt DAG along with the Meltano EL sync jobs that feed them is shown below:

```yaml
dags:
  generator_configs: []
  dag_definitions:
    full_dag:
      # Full DAG once a day end to end
      generator: dbt
      interval: '0 0 * * *'
      selection_rule: '*'
```

An example of "Source Based" approach where yu can see we use dbt graph operators to define the selection rules starting at a particular source and executing everything downstream:

```yaml
dags:
  generator_configs: []
  dag_definitions:
    full_dag:
      # Source based DAG once a day
      generator: dbt
      interval: '0 0 * * *'
      selection_rule: 'source:tap_gitlab.commits+'
```

An example of "Asset Based" approach where yu can see we again use dbt graph operators to define the selection rules but this time starting at a specific fact table and executing everything upstream:

```yaml
dags:
  generator_configs: []
  dag_definitions:
    full_dag:
      # Asset fact table based DAG once a day
      generator: dbt
      interval: '0 0 * * *'
      selection_rule: '+fact_commits'
```


#### Advanced Configuration

Sometimes there are tasks that you want to run outside after certain dbt models finish, this can be done using custom `steps`.
The following example shows running the full DAG, all Meltano EL syncs feeding it, and a custom step where we run an arbitrary Meltano command after the `fact_commit` dbt model completes:

```yaml
dags:
  generator_configs: []
  dag_definitions:
    full_dag:
      # Full DAG once a day end to end with custom task at the end
      generator: dbt
      interval: '0 0 * * *'
      selection_rule: '*'
      steps:
        - name: custom_task_something_extra
          cmd: 'meltano --version'
          depends_on:
            - model.my_meltano_project.fact_commit
```

Additionally, the dbt generator expects you to name your sources to match the Meltano tap that provided the data but in some cases this isn't ideal.
For this case you can use the `generator_config` to set the `source_tap_mapping` which tells the generator to use a different tap name for the specified dbt source.

```yaml
dags:
  generator_configs:
    dbt:
      default_target: "target-postgres"
      stream_level: true
      source_tap_mapping:
        tap_gitlab.commits: tap-gitlab-custom.commits
```

#### Other Utilities

Since all of your dbt DAGs are defined in configurations its now possible to analyze your configurations for potential mistakes.

For example you can run `python orchestrate/dags/dbt_analyze.py` which will compile all of your selection runs and let you know if there are any models that you have missed across all your DAG selection rules.
As a project gets bigger and the selection rules get more advanced it can be easy to lose track of what models are running in what DAG and potentially leave some stale.



## Usage

The generators use a `generator_cache.yml` file to pre-compile the information that it needs in order to build the DAGs.
This includes the dbt manifest.json, the Meltano schedules, and the output of each of your dbt DAG selection rules.
You can create the cache file by running `python orchestrate/dags/generator_cache_builder.py` or the generator will automatically create it itself if the file doesnt exist at runtime.

The advantages of doing it this way is that you don't need to install generator dependencies like Meltano in the Airflow webserver execution environment, which is particularly useful for Docker/Kubernetes deployments where Airflow and Meltano are run in separate containers.
In this case, the cache file can be used as a build artifact that gets generated during CI and packaged with the Airflow container.

Another advantage is that Airflow parses the DAG files every 30 seconds by default so its excessive to constantly be recomputing this information which requires running Meltano commands and parsing the dbt manifest.json files multiple times.

To refresh your cache file after making dbt, dag definition, or meltano schedule changes you can simply delete the file and either create one using the python script or let the generator create it automatically.
