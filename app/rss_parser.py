"""RSS解析和更新逻辑"""
import feedparser
import httpx
from datetime import datetime
from typing import Optional, Dict, List
from sqlalchemy.orm import Session
from app.database import RSSFeed, RSSItem, db
from loguru import logger


def parse_date(date_tuple: Optional[tuple]) -> Optional[datetime]:
    """解析日期元组（feedparser返回的time.struct_time）"""
    if not date_tuple:
        return None
    try:
        # feedparser 解析后的日期是 time.struct_time (9个元素的元组)
        if isinstance(date_tuple, tuple) and len(date_tuple) >= 6:
            return datetime(*date_tuple[:6])
    except Exception:
        pass
    return None


async def fetch_rss_feed(url: str) -> Optional[feedparser.FeedParserDict]:
    """获取并解析RSS源"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(str(url), follow_redirects=True)
            response.raise_for_status()
            feed = feedparser.parse(response.text)
            if feed.bozo and feed.bozo_exception:
                raise Exception(f"RSS解析错误: {feed.bozo_exception}")
            return feed
    except Exception as e:
        logger.error(f"获取RSS源失败 {url}: {e}")
        return None


async def update_feed(session: Session, feed_url: str) -> Optional[RSSFeed]:
    """更新RSS源及其条目"""
    # 获取或创建RSS源记录
    feed_record = session.query(RSSFeed).filter(RSSFeed.url == str(feed_url)).first()

    if not feed_record:
        feed_record = RSSFeed(url=str(feed_url))
        session.add(feed_record)
        session.flush()  # 获取ID

    # 获取RSS内容
    parsed_feed = await fetch_rss_feed(feed_url)
    if not parsed_feed:
        return None

    # 更新RSS源信息
    feed_record.title = parsed_feed.feed.get("title")
    feed_record.description = parsed_feed.feed.get("description")
    feed_record.link = parsed_feed.feed.get("link")

    # 解析最后更新时间
    updated_parsed = parsed_feed.feed.get("updated_parsed")
    if updated_parsed:
        feed_record.last_updated = parse_date(updated_parsed)
    else:
        feed_record.last_updated = datetime.utcnow()

    feed_record.updated_at = datetime.utcnow()

    # 更新条目
    existing_links = {
        item.link
        for item in session.query(RSSItem.link).filter(RSSItem.feed_id == feed_record.id).all()
    }

    new_items_count = 0
    for entry in parsed_feed.entries:
        link = entry.get("link")
        if not link or link in existing_links:
            continue

        # 创建新条目
        item = RSSItem(
            feed_id=feed_record.id,
            title=entry.get("title"),
            link=link,
            description=entry.get("description") or entry.get("summary"),
            published=parse_date(entry.get("published_parsed") or entry.get("updated_parsed")),
            author=entry.get("author")
        )
        session.add(item)
        existing_links.add(link)
        new_items_count += 1

    session.commit()
    logger.info(f"RSS源 {feed_url} 更新完成，新增 {new_items_count} 条条目")
    return feed_record


async def update_all_feeds():
    """更新所有RSS源"""
    session = db.get_session()
    try:
        feeds = session.query(RSSFeed).all()
        feed_urls = [feed.url for feed in feeds]
    finally:
        session.close()

    # 为每个feed创建独立的session
    for feed_url in feed_urls:
        session = db.get_session()
        try:
            await update_feed(session, feed_url)
        except Exception as e:
            logger.error(f"更新RSS源 {feed_url} 时出错: {e}")
            session.rollback()
        finally:
            session.close()
