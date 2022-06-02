CONTAINER_ID=$(docker ps -qf "ancestor=apache/superset:latest")
docker exec $CONTAINER_ID python /app/meltano/docker/compile_datasources.py
docker exec $CONTAINER_ID superset import_datasources -p /app/meltano/assets/databases/datasources.yml
