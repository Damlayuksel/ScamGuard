#!/bin/sh
# Shared helpers for the server scripts. Run the scripts from anywhere; they cd to the
# repository root.
set -eu

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
ENV_FILE="${REPO_ROOT}/infra/.env.prod"

cd "${REPO_ROOT}"

if [ ! -f "${ENV_FILE}" ]; then
    echo "Missing ${ENV_FILE}. Copy infra/.env.prod.example and fill it in." >&2
    exit 1
fi

# Read a single value from infra/.env.prod without sourcing the whole file.
env_value() {
    sed -n "s/^$1=//p" "${ENV_FILE}" | tail -n 1
}

compose() {
    docker compose -f infra/docker-compose.prod.yml --env-file "${ENV_FILE}" "$@"
}
