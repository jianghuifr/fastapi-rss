"""数据库连接和模型定义"""
import os
from sqlalchemy import create_engine, Column, String, DateTime, Text, Integer, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime
from pathlib import Path
from loguru import logger

Base = declarative_base()


class User(Base):
    """用户表（用于管理面板认证）"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String, unique=True, nullable=False, index=True)
    email = Column(String, unique=True, nullable=True, index=True)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class RSSFeed(Base):
    """RSS源表"""
    __tablename__ = "rss_feeds"

    id = Column(Integer, primary_key=True, autoincrement=True)
    url = Column(String, unique=True, nullable=False, index=True)
    title = Column(String)
    description = Column(Text)
    link = Column(String)
    last_updated = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class RSSItem(Base):
    """RSS条目表"""
    __tablename__ = "rss_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    feed_id = Column(Integer, nullable=False, index=True)
    title = Column(String)
    link = Column(String, unique=True, nullable=False, index=True)
    description = Column(Text)
    ai_summary = Column(Text)  # AI 总结
    published = Column(DateTime)
    author = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)


class Database:
    """数据库管理类"""

    def __init__(self, db_path: str = None):
        if db_path is None:
            # 默认使用 SQLite，也可以使用 DuckDB
            db_type = os.getenv("DB_TYPE", "sqlite").lower()
            if db_type == "duckdb":
                db_path = os.getenv("DB_PATH", "data/rss.duckdb")
                # DuckDB 需要 duckdb-engine 包
                try:
                    self.engine = create_engine(f"duckdb:///{db_path}")
                except Exception:
                    # 如果 duckdb-engine 不可用，回退到 SQLite
                    logger.warning("DuckDB 引擎不可用，使用 SQLite")
                    db_path = os.getenv("DB_PATH", "data/rss.db")
                    self.engine = create_engine(
                        f"sqlite:///{db_path}",
                        connect_args={"check_same_thread": False}
                    )
            else:
                db_path = os.getenv("DB_PATH", "data/rss.db")
                self.engine = create_engine(
                    f"sqlite:///{db_path}",
                    connect_args={"check_same_thread": False}
                )
        else:
            if db_path.endswith(".duckdb"):
                try:
                    self.engine = create_engine(f"duckdb:///{db_path}")
                except Exception:
                    db_path = db_path.replace(".duckdb", ".db")
                    self.engine = create_engine(
                        f"sqlite:///{db_path}",
                        connect_args={"check_same_thread": False}
                    )
            else:
                self.engine = create_engine(
                    f"sqlite:///{db_path}",
                    connect_args={"check_same_thread": False}
                )

        self.db_path = Path(db_path)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self._init_db()

    def _init_db(self):
        """初始化数据库表"""
        Base.metadata.create_all(bind=self.engine)

    def get_session(self):
        """获取数据库会话"""
        return self.SessionLocal()

    def close(self):
        """关闭数据库连接"""
        self.engine.dispose()


# 全局数据库实例
db = Database()
