#!/usr/bin/env bash
#
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
set -e

python /app/meltano/docker/compile_datasources.py

if [ -f "/app/superset_home/superset.db" ]; then
  SUPERSET_DB_EXISTS=true
else
  SUPERSET_DB_EXISTS=false
fi

#
# Always install local overrides first
#

REQUIREMENTS_LOCAL="/app/superset_home/requirements-local.txt"
#
# Make sure we have dev requirements installed
#
if [ -f "${REQUIREMENTS_LOCAL}" ]; then
  echo "Installing local overrides at ${REQUIREMENTS_LOCAL}"
  pip install -r "${REQUIREMENTS_LOCAL}"
else
  echo "Skipping local overrides"
fi


STEP_CNT=6

echo_step() {
cat <<EOF

######################################################################


Init Step ${1}/${STEP_CNT} [${2}] -- ${3}


######################################################################

EOF
}
ADMIN_PASSWORD="admin"
# Initialize the database
echo_step "1" "Starting" "Applying DB migrations"
superset db upgrade
echo_step "1" "Complete" "Applying DB migrations"

# Create an admin user
echo_step "2" "Starting" "Setting up admin user ( admin / $ADMIN_PASSWORD )"
superset fab create-admin \
              --username admin \
              --firstname Superset \
              --lastname Admin \
              --email admin@superset.com \
              --password $ADMIN_PASSWORD
echo_step "2" "Complete" "Setting up admin user"
# Create default roles and permissions
echo_step "3" "Starting" "Setting up roles and perms"
superset init
echo_step "3" "Complete" "Setting up roles and perms"

if [ "$SUPERSET_LOAD_EXAMPLES" = "true" ]; then
    # Load some data to play with
    echo_step "4" "Starting" "Loading examples"
    superset load_examples
    echo_step "4" "Complete" "Loading examples"
else
    echo_step "4" "Skipping" "Loading examples"
fi

if "$SUPERSET_SYNC_ASSETS" = "true" && ! $SUPERSET_DB_EXISTS; then
    echo_step "5" "Starting" "Loading assets"
    superset import_datasources -p /app/superset_home/datasources.yml
else
    echo_step "5" "Skipping" "Loading assets"
fi

echo_step "6" "Starting" "Removing datasources.yml"
rm /app/superset_home/datasources.yml
echo_step "6" "Complete" "Removing datasources.yml"

gunicorn \
    --bind  "0.0.0.0:${SUPERSET_PORT}" \
    --access-logfile '-' \
    --error-logfile '-' \
    --workers 1 \
    --worker-class gthread \
    --threads 20 \
    --timeout ${GUNICORN_TIMEOUT:-60} \
    --limit-request-line 0 \
    --limit-request-field_size 0 \
    "${FLASK_APP}"
