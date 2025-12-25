"""FastAPI路由定义"""
from fastapi import APIRouter, HTTPException, Depends, Query, UploadFile, File, status
from fastapi.responses import Response
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta
import io
import asyncio
from xml.etree.ElementTree import Element, SubElement, tostring, parse
from xml.dom import minidom
from html import escape
from app.database import db, RSSFeed, RSSItem
from loguru import logger
from app.models import (
    RSSFeedCreate,
    RSSFeedResponse,
    RSSItemResponse,
    FeedListResponse,
    ItemListResponse,
    LoginRequest,
    LoginResponse
)
from app.rss_parser import update_feed
from app.ai_summary import ai_summary_service
from app.auth import authenticate_user, create_access_token, get_current_user, get_current_superuser
from worker.tasks import update_single_feed_task, update_all_feeds_task
from worker.celery_app import celery_app
from celery.result import AsyncResult

router = APIRouter(prefix="/api/v1", tags=["RSS"])
auth_router = APIRouter(prefix="/api/v1/auth", tags=["认证"])


def get_db():
    """获取数据库会话依赖"""
    session = db.get_session()
    try:
        yield session
    finally:
        session.close()


# 认证路由
@auth_router.post("/login", response_model=LoginResponse)
def login(login_data: LoginRequest, session: Session = Depends(get_db)):
    """用户登录"""
    user = authenticate_user(session, login_data.username, login_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(data={"sub": user.username})
    return LoginResponse(access_token=access_token)


@router.post("/feeds", response_model=RSSFeedResponse, status_code=201)
async def create_feed(
    feed: RSSFeedCreate,
    session: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """添加新的RSS源（需要认证）"""
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
def delete_feed(
    feed_id: int,
    session: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """删除RSS源（需要认证）"""
    feed = session.query(RSSFeed).filter(RSSFeed.id == feed_id).first()
    if not feed:
        raise HTTPException(status_code=404, detail="RSS源不存在")

    # 删除关联的条目
    session.query(RSSItem).filter(RSSItem.feed_id == feed_id).delete()
    session.delete(feed)
    session.commit()
    return None


@router.post("/feeds/{feed_id}/update", response_model=RSSFeedResponse)
async def update_feed_endpoint(
    feed_id: int,
    session: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """手动更新RSS源（需要认证）"""
    feed = session.query(RSSFeed).filter(RSSFeed.id == feed_id).first()
    if not feed:
        raise HTTPException(status_code=404, detail="RSS源不存在")

    updated_feed = await update_feed(session, feed.url)
    if not updated_feed:
        raise HTTPException(status_code=400, detail="更新失败")

    return RSSFeedResponse.model_validate(updated_feed)


@router.post("/feeds/{feed_id}/update-async")
def update_feed_async(
    feed_id: int,
    session: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """异步更新RSS源（使用Celery，需要认证）"""
    feed = session.query(RSSFeed).filter(RSSFeed.id == feed_id).first()
    if not feed:
        raise HTTPException(status_code=404, detail="RSS源不存在")

    task = update_single_feed_task.delay(str(feed.url))
    return {"task_id": task.id, "status": "pending"}


async def _add_ai_summaries(items: List[RSSItem], session: Session) -> List[RSSItemResponse]:
    """为 items 添加 AI 总结（优先使用数据库中的，如果没有则生成并保存）"""
    # 并发生成 AI 总结
    async def process_item(item: RSSItem):
        item_dict = RSSItemResponse.model_validate(item).model_dump()

        # 如果数据库中已有 AI 总结，直接使用
        if item.ai_summary:
            item_dict["ai_summary"] = item.ai_summary
            logger.debug(f"使用数据库中已有的 AI 总结（条目 {item.id}）")
            return RSSItemResponse(**item_dict)

        # 如果没有，生成新的 AI 总结
        if item.link:
            try:
                summary = await ai_summary_service.summarize(
                    title=item.title or "",
                    link=item.link
                )
                if summary:
                    # 保存到数据库
                    try:
                        # 重新查询以确保获取最新数据，避免并发冲突
                        from app.database import db
                        update_session = db.get_session()
                        try:
                            update_item = update_session.query(RSSItem).filter(RSSItem.id == item.id).first()
                            if update_item:
                                # 再次检查是否已有总结（避免并发重复保存）
                                if not update_item.ai_summary:
                                    update_item.ai_summary = summary
                                    update_session.commit()
                                    logger.success(f"成功为条目 {item.id} ({item.title[:50] if item.title else '无标题'}) 生成并保存 AI 总结")
                                else:
                                    # 如果已经有总结，使用数据库中的
                                    summary = update_item.ai_summary
                                    logger.debug(f"条目 {item.id} 的 AI 总结已被其他请求保存，使用数据库中的版本")
                        except Exception as db_error:
                            update_session.rollback()
                            logger.warning(f"保存 AI 总结到数据库时出错: {str(db_error)}")
                        finally:
                            update_session.close()
                    except Exception as e:
                        logger.warning(f"创建数据库会话失败: {str(e)}")
                else:
                    logger.warning(f"条目 {item.id} 的 AI 总结返回 None（可能 API 调用失败或返回空）")
                item_dict["ai_summary"] = summary
            except Exception as e:
                logger.error(f"为条目 {item.id} 生成 AI 总结时出错: {str(e)}")
                item_dict["ai_summary"] = None
        else:
            logger.warning(f"条目 {item.id} 没有 link，跳过 AI 总结")

        return RSSItemResponse(**item_dict)

    # 并发处理所有 items
    tasks = [process_item(item) for item in items]
    item_responses = await asyncio.gather(*tasks, return_exceptions=True)

    # 处理异常情况
    result = []
    for idx, resp in enumerate(item_responses):
        if isinstance(resp, Exception):
            # 如果 AI 总结失败，返回不带总结的响应
            logger.error(f"处理条目 {items[idx].id} 时发生异常: {str(resp)}")
            result.append(RSSItemResponse.model_validate(items[idx]))
        else:
            result.append(resp)

    return result


@router.get("/feeds/{feed_id}/items", response_model=ItemListResponse)
async def get_feed_items(
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

    # 添加 AI 总结
    item_responses = await _add_ai_summaries(items, session)

    return ItemListResponse(
        items=item_responses,
        total=total
    )


@router.get("/items", response_model=ItemListResponse)
async def list_all_items(
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

    # 添加 AI 总结
    item_responses = await _add_ai_summaries(items, session)

    return ItemListResponse(
        items=item_responses,
        total=total
    )


@router.get("/items/{item_id}", response_model=RSSItemResponse)
async def get_item(item_id: int, session: Session = Depends(get_db)):
    """获取单个条目详情"""
    item = session.query(RSSItem).filter(RSSItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="条目不存在")

    # 添加 AI 总结
    item_responses = await _add_ai_summaries([item], session)
    return item_responses[0]


@router.get("/ai/config")
def get_ai_config():
    """获取 AI 配置状态（用于调试）"""
    return ai_summary_service.get_config()


@router.post("/ai/test")
async def test_ai_summary(title: str = "测试标题", link: str = "https://example.com/article"):
    """测试 AI 总结功能"""
    summary = await ai_summary_service.summarize(title, link)
    return {
        "success": summary is not None,
        "summary": summary,
        "config": ai_summary_service.get_config()
    }


@router.get("/tasks/{task_id}")
def get_task_status(task_id: str):
    """获取Celery任务状态"""
    task_result = AsyncResult(task_id, app=celery_app)
    return {
        "task_id": task_id,
        "status": task_result.status,
        "result": task_result.result if task_result.ready() else None,
        "traceback": task_result.traceback if task_result.failed() else None,
    }


@router.get("/tasks")
def list_tasks(limit: int = Query(50, ge=1, le=100)):
    """获取最近的Celery任务列表（从Redis获取）"""
    # 注意：这需要配置Celery结果后端为Redis
    # 实际实现中可能需要使用Flower或其他监控工具
    # 这里提供一个简化版本
    return {
        "tasks": [],
        "total": 0,
        "message": "任务历史需要配置Celery监控工具（如Flower）"
    }


@router.post("/tasks/update-all")
def trigger_update_all(current_user = Depends(get_current_user)):
    """手动触发更新所有RSS源的任务（需要认证）"""
    task = update_all_feeds_task.delay()
    return {"task_id": task.id, "status": "pending", "message": "已触发更新所有RSS源任务"}


@router.get("/feeds/{feed_id}/stats")
def get_feed_stats(feed_id: int, session: Session = Depends(get_db)):
    """获取RSS源的统计信息"""
    feed = session.query(RSSFeed).filter(RSSFeed.id == feed_id).first()
    if not feed:
        raise HTTPException(status_code=404, detail="RSS源不存在")

    total_items = session.query(RSSItem).filter(RSSItem.feed_id == feed_id).count()
    latest_item = session.query(RSSItem).filter(
        RSSItem.feed_id == feed_id
    ).order_by(
        RSSItem.published.desc().nullslast(),
        RSSItem.created_at.desc()
    ).first()

    return {
        "feed_id": feed_id,
        "total_items": total_items,
        "last_updated": feed.last_updated.isoformat() if feed.last_updated else None,
        "latest_item": {
            "title": latest_item.title,
            "published": latest_item.published.isoformat() if latest_item.published else None,
        } if latest_item else None,
    }


@router.get("/feeds/export/opml")
def export_opml(
    session: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """导出所有RSS源为OPML文件（需要认证）"""
    feeds = session.query(RSSFeed).order_by(RSSFeed.created_at.desc()).all()

    # 创建OPML根元素
    opml = Element("opml")
    opml.set("version", "2.0")

    # 添加head元素
    head = SubElement(opml, "head")
    title = SubElement(head, "title")
    title.text = "RSS订阅列表"
    date_created = SubElement(head, "dateCreated")
    date_created.text = datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT")

    # 添加body元素
    body = SubElement(opml, "body")

    # 为每个feed创建outline元素
    for feed in feeds:
        outline = SubElement(body, "outline")
        outline.set("type", "rss")
        # 转义特殊字符
        feed_title = escape(feed.title or feed.url) if feed.title else feed.url
        outline.set("text", feed_title)
        outline.set("title", feed_title)
        outline.set("xmlUrl", feed.url)
        if feed.link:
            outline.set("htmlUrl", feed.link)
        if feed.description:
            outline.set("description", escape(feed.description))

    # 生成格式化的XML字符串
    rough_string = tostring(opml, encoding="unicode")
    reparsed = minidom.parseString(rough_string)
    xml_string = reparsed.toprettyxml(indent="  ", encoding="UTF-8").decode("utf-8")

    # 返回文件响应
    return Response(
        content=xml_string,
        media_type="application/xml",
        headers={
            "Content-Disposition": f'attachment; filename="rss_feeds_{datetime.now().strftime("%Y%m%d_%H%M%S")}.opml"'
        }
    )


@router.post("/feeds/import/opml")
async def import_opml(
    file: UploadFile = File(...),
    session: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    从OPML文件导入RSS源

    接收前端上传的文件，在后端完成所有解析和处理工作：
    1. 验证文件格式
    2. 读取文件内容
    3. 解析OPML XML结构
    4. 提取所有RSS源
    5. 导入到数据库
    """
    # 验证文件格式
    if not file.filename or not file.filename.endswith('.opml'):
        raise HTTPException(status_code=400, detail="文件必须是OPML格式")

    try:
        # 读取文件内容（二进制）
        content = await file.read()

        # 在后端解析XML文件
        root = parse(io.BytesIO(content)).getroot()

        # 查找所有outline元素
        imported_count = 0
        skipped_count = 0
        errors = []

        def extract_outlines(element, parent_title=""):
            """递归提取所有outline元素"""
            outlines = []
            for child in element:
                if child.tag == "outline":
                    # 检查是否有xmlUrl属性（RSS源）
                    xml_url = child.get("xmlUrl") or child.get("xmlURL")
                    if xml_url:
                        outlines.append({
                            "url": xml_url,
                            "title": child.get("text") or child.get("title") or parent_title,
                            "html_url": child.get("htmlUrl") or child.get("htmlURL"),
                            "description": child.get("description")
                        })
                    # 递归处理嵌套的outline
                    child_title = child.get("text") or child.get("title") or parent_title
                    outlines.extend(extract_outlines(child, child_title))
            return outlines

        # 从body元素开始提取
        body = root.find("body")
        if body is None:
            raise HTTPException(status_code=400, detail="OPML文件格式错误：缺少body元素")

        outlines = extract_outlines(body)

        if not outlines:
            raise HTTPException(status_code=400, detail="OPML文件中没有找到RSS源")

        # 导入每个RSS源
        for outline in outlines:
            try:
                feed_url = outline["url"]
                # 检查是否已存在
                existing = session.query(RSSFeed).filter(RSSFeed.url == feed_url).first()
                if existing:
                    skipped_count += 1
                    continue

                # 创建并更新feed
                feed_record = await update_feed(session, feed_url)
                if feed_record:
                    imported_count += 1
                else:
                    errors.append(f"无法解析RSS源: {feed_url}")
            except Exception as e:
                errors.append(f"导入失败 {outline.get('url', '未知')}: {str(e)}")

        session.commit()

        return {
            "message": "导入完成",
            "imported": imported_count,
            "skipped": skipped_count,
            "errors": errors,
            "total": len(outlines)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"解析OPML文件失败: {str(e)}")
