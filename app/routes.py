"""FastAPI路由定义"""
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import db, RSSFeed, RSSItem
from app.models import (
    RSSFeedCreate,
    RSSFeedResponse,
    RSSItemResponse,
    FeedListResponse,
    ItemListResponse
)
from app.rss_parser import update_feed
from worker.tasks import update_single_feed_task

router = APIRouter(prefix="/api/v1", tags=["RSS"])


def get_db():
    """获取数据库会话依赖"""
    session = db.get_session()
    try:
        yield session
    finally:
        session.close()


@router.post("/feeds", response_model=RSSFeedResponse, status_code=201)
async def create_feed(feed: RSSFeedCreate, session: Session = Depends(get_db)):
    """添加新的RSS源"""
    # 检查是否已存在
    existing = session.query(RSSFeed).filter(RSSFeed.url == str(feed.url)).first()
    if existing:
        raise HTTPException(status_code=400, detail="RSS源已存在")

    # 创建并立即更新
    feed_record = await update_feed(session, str(feed.url))
    if not feed_record:
        raise HTTPException(status_code=400, detail="无法解析RSS源")

    return RSSFeedResponse.model_validate(feed_record)


@router.get("/feeds", response_model=FeedListResponse)
def list_feeds(session: Session = Depends(get_db)):
    """获取所有RSS源列表"""
    feeds = session.query(RSSFeed).order_by(RSSFeed.created_at.desc()).all()
    return FeedListResponse(
        feeds=[RSSFeedResponse.model_validate(feed) for feed in feeds],
        total=len(feeds)
    )


@router.get("/feeds/{feed_id}", response_model=RSSFeedResponse)
def get_feed(feed_id: int, session: Session = Depends(get_db)):
    """获取单个RSS源详情"""
    feed = session.query(RSSFeed).filter(RSSFeed.id == feed_id).first()
    if not feed:
        raise HTTPException(status_code=404, detail="RSS源不存在")
    return RSSFeedResponse.model_validate(feed)


@router.delete("/feeds/{feed_id}", status_code=204)
def delete_feed(feed_id: int, session: Session = Depends(get_db)):
    """删除RSS源"""
    feed = session.query(RSSFeed).filter(RSSFeed.id == feed_id).first()
    if not feed:
        raise HTTPException(status_code=404, detail="RSS源不存在")

    # 删除关联的条目
    session.query(RSSItem).filter(RSSItem.feed_id == feed_id).delete()
    session.delete(feed)
    session.commit()
    return None


@router.post("/feeds/{feed_id}/update", response_model=RSSFeedResponse)
async def update_feed_endpoint(feed_id: int, session: Session = Depends(get_db)):
    """手动更新RSS源"""
    feed = session.query(RSSFeed).filter(RSSFeed.id == feed_id).first()
    if not feed:
        raise HTTPException(status_code=404, detail="RSS源不存在")

    updated_feed = await update_feed(session, feed.url)
    if not updated_feed:
        raise HTTPException(status_code=400, detail="更新失败")

    return RSSFeedResponse.model_validate(updated_feed)


@router.post("/feeds/{feed_id}/update-async")
def update_feed_async(feed_id: int, session: Session = Depends(get_db)):
    """异步更新RSS源（使用Celery）"""
    feed = session.query(RSSFeed).filter(RSSFeed.id == feed_id).first()
    if not feed:
        raise HTTPException(status_code=404, detail="RSS源不存在")

    task = update_single_feed_task.delay(str(feed.url))
    return {"task_id": task.id, "status": "pending"}


@router.get("/feeds/{feed_id}/items", response_model=ItemListResponse)
def get_feed_items(
    feed_id: int,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_db)
):
    """获取RSS源的条目列表"""
    feed = session.query(RSSFeed).filter(RSSFeed.id == feed_id).first()
    if not feed:
        raise HTTPException(status_code=404, detail="RSS源不存在")

    items = session.query(RSSItem).filter(
        RSSItem.feed_id == feed_id
    ).order_by(
        RSSItem.published.desc().nullslast(),
        RSSItem.created_at.desc()
    ).offset(offset).limit(limit).all()

    total = session.query(RSSItem).filter(RSSItem.feed_id == feed_id).count()

    return ItemListResponse(
        items=[RSSItemResponse.model_validate(item) for item in items],
        total=total
    )


@router.get("/items", response_model=ItemListResponse)
def list_all_items(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    feed_id: Optional[int] = Query(None),
    session: Session = Depends(get_db)
):
    """获取所有条目列表"""
    query = session.query(RSSItem)
    if feed_id:
        query = query.filter(RSSItem.feed_id == feed_id)

    items = query.order_by(
        RSSItem.published.desc().nullslast(),
        RSSItem.created_at.desc()
    ).offset(offset).limit(limit).all()

    total = query.count()

    return ItemListResponse(
        items=[RSSItemResponse.model_validate(item) for item in items],
        total=total
    )


@router.get("/items/{item_id}", response_model=RSSItemResponse)
def get_item(item_id: int, session: Session = Depends(get_db)):
    """获取单个条目详情"""
    item = session.query(RSSItem).filter(RSSItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="条目不存在")
    return RSSItemResponse.model_validate(item)
