"""快速测试脚本 - 添加示例RSS源"""
import asyncio
import sys
from app.database import db
from app.rss_parser import update_feed

async def main():
    """添加示例RSS源"""
    session = db.get_session()
    try:
        feed_url = "https://www.ruanyifeng.com/blog/atom.xml"
        print(f"正在添加RSS源: {feed_url}")
        result = await update_feed(session, feed_url)
        if result:
            print(f"✓ RSS源添加成功!")
            print(f"  标题: {result.title}")
            print(f"  描述: {result.description}")
        else:
            print("✗ RSS源添加失败")
            sys.exit(1)
    except Exception as e:
        print(f"✗ 错误: {e}")
        sys.exit(1)
    finally:
        session.close()

if __name__ == "__main__":
    asyncio.run(main())
