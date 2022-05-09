CONTAINER_ID=$(docker ps -qf "ancestor=apache/superset:latest")
docker exec $CONTAINER_ID superset import-dashboards -p /app/assets/dashboard/dashboards.json
