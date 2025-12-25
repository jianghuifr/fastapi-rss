"""Pydantic 模型定义"""
from pydantic import BaseModel, HttpUrl, field_serializer
from datetime import datetime, timezone
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

    @field_serializer('last_updated', 'created_at', 'updated_at', when_used='json')
    def serialize_datetime(self, value: Optional[datetime], _info) -> Optional[str]:
        """序列化 datetime 为 ISO 8601 格式，带 UTC 时区标识"""
        if value is None:
            return None
        # 确保返回 UTC 时间，带 Z 后缀
        if value.tzinfo is None:
            # 如果没有时区信息，假设是 UTC
            value = value.replace(tzinfo=timezone.utc)
        return value.isoformat().replace('+00:00', 'Z')

    class Config:
        from_attributes = True


class RSSItemResponse(BaseModel):
    """RSS条目响应模型"""
    id: int
    feed_id: int
    title: Optional[str] = None
    link: str
    description: Optional[str] = None
    ai_summary: Optional[str] = None  # AI 总结
    published: Optional[datetime] = None
    author: Optional[str] = None
    created_at: datetime

    @field_serializer('published', 'created_at', when_used='json')
    def serialize_datetime(self, value: Optional[datetime], _info) -> Optional[str]:
        """序列化 datetime 为 ISO 8601 格式，带 UTC 时区标识"""
        if value is None:
            return None
        # 确保返回 UTC 时间，带 Z 后缀
        if value.tzinfo is None:
            # 如果没有时区信息，假设是 UTC
            value = value.replace(tzinfo=timezone.utc)
        return value.isoformat().replace('+00:00', 'Z')

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


class LoginRequest(BaseModel):
    """登录请求模型"""
    username: str
    password: str


class LoginResponse(BaseModel):
    """登录响应模型"""
    access_token: str
    token_type: str = "bearer"
