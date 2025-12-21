#!/bin/bash

reset || true

set -e

if [[ -z ${ENV} ]]; then
    source .env 2>/dev/null || true
fi

# 检查参数
MODE="app"
for arg in "$@"
do
    case "$arg" in
        --app)
            MODE="app"
            ;;
        --worker)
            MODE="worker"
            ;;
        --beat)
            MODE="beat"
            ;;
        --dev)
            MODE="dev"
            ;;
    esac
done

if [[ "$MODE" == "worker" ]]; then
    # 启动 Celery worker
    exec uv run celery -A worker.celery_app worker --loglevel=info
elif [[ "$MODE" == "beat" ]]; then
    # 启动 Celery beat (定时任务调度器)
    exec uv run celery -A worker.celery_app beat --loglevel=info
elif [[ "$MODE" == "dev" ]]; then
    # 开发模式
    exec uv run uvicorn app.main:app --host 0.0.0.0 --port ${FASTAPI_RSS_PORT:-8000} --reload
else
    # 生产模式运行 FastAPI
    exec uv run uvicorn app.main:app --host 0.0.0.0 --port ${FASTAPI_RSS_PORT:-8000}
fi
