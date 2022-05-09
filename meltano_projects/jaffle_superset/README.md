# Meltano x dbt Jaffle Shop + Superset

This project is based on the dbt's classic [Jaffle shop example project](https://github.com/dbt-labs/jaffle_shop) but in a Meltano context and builds off the [singer_dbt_jaffle](../singer_dbt_jaffle/) sample project in this repo.

### What is this repo?

A Meltano project to share the benefits of running dbt core within a Meltano project.
It can also serve as an example of how to configure your own Meltano project.

The idea is to use dbt's Jaffle shop example project but instead of using dbt seed to load the data into your warehouse (aka local Postgres instance) you will use tap-csv and target-postgres to simulate how to use Singer as a EL tool.

### What's contained in this project?

The Meltano project has the following plugins installed and configured:

- EL
    - tap-csv (Singer)
    - target-postgres (Singer)
- Transformation
    - dbt

### Prerequisites

Having Meltano installed! See https://docs.meltano.com/guide/installation for more details.

### How to run this project?

1. Clone this repo:

    ```bash
    git clone https://github.com/pnadolny13/meltano_example_implementations.git
    cd meltano_example_implementations/meltano_projects/singer_dbt_jaffle/
    ```

1. Install Meltano:

    ```bash
    meltano install
    ```

1. Start a local Postgres docker instance.
It will contain a database called `warehouse` that we'll send our raw data to.

    ```bash
    docker run --rm --name postgres -e POSTGRES_PASSWORD=meltano -e POSTGRES_USER=meltano -e POSTGRES_DB=warehouse -d -p 5432:5432 postgres
    ```

1. Create a `.env` file and add database secrets. This is mostly to encourage best practices since were using a local Postgres instance we don't have any sensitive credentials.

    ```bash
    touch .env
    echo PG_PASSWORD="meltano" >> .env
    ```

1. Run the EL+T pipeline using Meltano

    ```bash
    meltano run tap-csv target-postgres dbt:run
    ```

    You should now see data in your Postgres database.

1. Start Superset

    ```bash
    touch analyze/superset/docker/.env
    meltano invoke superset:ui
    ```

1. Navigate to http://localhost:8088/ and use `admin` `admin` as username and password, then click the drop down Data -> Datasets and start exploring the jaffle shop datasets.
