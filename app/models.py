"""Pydantic 模型定义"""
from pydantic import BaseModel, HttpUrl
from datetime import datetime
from typing import Optional, List


class RSSFeedCreate(BaseModel):
    """创建RSS源的请求模型"""
    url: HttpUrl


class RSSFeedResponse(BaseModel):
    """RSS源响应模型"""
    id: int
    url: str
    title: Optional[str] = None
    description: Optional[str] = None
    link: Optional[str] = None
    last_updated: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class RSSItemResponse(BaseModel):
    """RSS条目响应模型"""
    id: int
    feed_id: int
    title: Optional[str] = None
    link: str
    description: Optional[str] = None
    published: Optional[datetime] = None
    author: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class FeedListResponse(BaseModel):
    """RSS源列表响应"""
    feeds: List[RSSFeedResponse]
    total: int


class ItemListResponse(BaseModel):
    """RSS条目列表响应"""
    items: List[RSSItemResponse]
    total: int
