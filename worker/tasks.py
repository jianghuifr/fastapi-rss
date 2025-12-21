"""Celery任务定义"""
from worker.celery_app import celery_app
from app.rss_parser import update_all_feeds, update_feed
from app.database import db
from sqlalchemy.orm import Session


@celery_app.task(name="worker.tasks.update_all_feeds_task")
def update_all_feeds_task():
    """定时更新所有RSS源的任务"""
    import asyncio
    try:
        asyncio.run(update_all_feeds())
        return {"status": "success", "message": "所有RSS源更新完成"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@celery_app.task(name="worker.tasks.update_single_feed_task")
def update_single_feed_task(feed_url: str):
    """更新单个RSS源的任务"""
    import asyncio
    session = db.get_session()
    try:
        result = asyncio.run(update_feed(session, feed_url))
        if result:
            return {"status": "success", "message": f"RSS源 {feed_url} 更新成功"}
        else:
            return {"status": "error", "message": f"RSS源 {feed_url} 更新失败"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        session.close()
