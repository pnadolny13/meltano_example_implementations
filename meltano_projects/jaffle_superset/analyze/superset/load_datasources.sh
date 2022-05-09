python analyze/superset/compile_datasources.py
CONTAINER_ID=$(docker ps -qf "ancestor=apache/superset:latest")
docker exec $CONTAINER_ID superset import_datasources -p /app/assets/database/datasources.yml
