CONTAINER_ID=$(docker ps -qf "ancestor=apache/superset:latest")
docker exec $CONTAINER_ID superset export-dashboards -f /app/assets/dashboard/dashboards.json
