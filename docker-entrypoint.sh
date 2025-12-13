#!/bin/bash

reset || true

set -e

if [[ -z ${ENV} ]]; then
    source .env
fi

FASTAPI_RSS_DEV=${FASTAPI_RSS_DEV:-false}
for arg in "$@"
do
    if [[ "$arg" == "--dev" ]]; then
        FASTAPI_RSS_DEV=true
        break
    fi
done

if [[ "$FASTAPI_RSS_DEV" == true ]]; then
    exec uv run fastapi dev --port ${FASTAPI_RSS_PORT:-8000} api/main.py
else
    exec uv run fastapi run --port ${FASTAPI_RSS_PORT:-8000} api/main.py
fi
