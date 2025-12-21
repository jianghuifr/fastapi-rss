"""Celery应用配置"""
from celery import Celery
import os

# Redis作为消息代理
redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "rss_worker",
    broker=redis_url,
    backend=redis_url,
    include=["worker.tasks"]
)

# Celery配置
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
    # 定时任务配置
    beat_schedule={
        "update-all-feeds": {
            "task": "worker.tasks.update_all_feeds_task",
            "schedule": 300.0,  # 每5分钟执行一次
        },
    },
)
