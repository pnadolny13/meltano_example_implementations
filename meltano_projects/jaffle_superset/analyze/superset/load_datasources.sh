python analyze/superset/compile_datasources.py
docker compose -f analyze/superset/docker-compose.yml exec superset superset import_datasources -p /app/assets/database/datasources.yml
