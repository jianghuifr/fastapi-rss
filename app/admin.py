"""SQLAdmin 管理面板配置"""
import os
from sqladmin import Admin, ModelView, BaseView
from sqladmin.authentication import AuthenticationBackend
from fastapi import Request, UploadFile, File, Depends
from fastapi.responses import Response, HTMLResponse, RedirectResponse
from starlette.responses import RedirectResponse as StarletteRedirectResponse
from sqlalchemy.orm import Session
from app.database import Base, RSSFeed, RSSItem, User, db
from app.auth import authenticate_user, create_access_token, verify_token, get_password_hash, get_current_user
from app.routes import get_db
from app.rss_parser import update_feed
from xml.etree.ElementTree import Element, SubElement, tostring, parse
from xml.dom import minidom
from html import escape
from datetime import datetime
import io
from loguru import logger

# 创建认证后端
class AdminAuth(AuthenticationBackend):
    async def login(self, request: Request) -> bool:
        form = await request.form()
        username = form.get("username")
        password = form.get("password")

        if not username or not password:
            return False

        session = db.get_session()
        try:
            user = authenticate_user(session, username, password)
            if user:
                # 创建 token
                access_token = create_access_token(data={"sub": user.username})
                request.session.update({"token": access_token})
                return True
        finally:
            session.close()
        return False

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> bool:
        token = request.session.get("token")
        if not token:
            return False
        payload = verify_token(token)
        if payload is None:
            return False
        # 验证用户是否仍然存在且活跃
        session = db.get_session()
        try:
            username = payload.get("sub")
            user = session.query(User).filter(User.username == username).first()
            if user and user.is_active:
                return True
        finally:
            session.close()
        return False


# 创建管理面板视图
class RSSFeedAdmin(ModelView, model=RSSFeed):
    """RSS源管理"""
    column_list = [RSSFeed.id, RSSFeed.title, RSSFeed.url, RSSFeed.created_at, RSSFeed.last_updated]
    column_searchable_list = [RSSFeed.title, RSSFeed.url]
    column_sortable_list = [RSSFeed.id, RSSFeed.created_at, RSSFeed.last_updated]
    column_details_exclude_list = [RSSFeed.description]
    can_create = True
    can_edit = True
    can_delete = True
    can_view_details = True
    name = "RSS源"
    name_plural = "RSS源"


class RSSItemAdmin(ModelView, model=RSSItem):
    """RSS条目管理"""
    column_list = [RSSItem.id, RSSItem.title, RSSItem.feed_id, RSSItem.published, RSSItem.created_at]
    column_searchable_list = [RSSItem.title, RSSItem.link]
    column_sortable_list = [RSSItem.id, RSSItem.published, RSSItem.created_at]
    column_details_exclude_list = [RSSItem.description, RSSItem.ai_summary]
    can_create = False  # RSS条目通常由系统自动创建
    can_edit = True
    can_delete = True
    can_view_details = True
    name = "RSS条目"
    name_plural = "RSS条目"


class UserAdmin(ModelView, model=User):
    """用户管理"""
    column_list = [User.id, User.username, User.email, User.is_active, User.is_superuser, User.created_at]
    column_searchable_list = [User.username, User.email]
    column_sortable_list = [User.id, User.created_at]
    can_create = True
    can_edit = True
    can_delete = True
    can_view_details = True
    name = "用户"
    name_plural = "用户"

    # 密码字段特殊处理 - 在表单中隐藏，通过其他方式设置
    form_excluded_columns = [User.hashed_password]

    # 注意：在 sqladmin 中创建/编辑用户时，需要手动设置密码哈希
    # 建议通过 API 或脚本创建用户，而不是通过管理面板


# OPML 管理功能（直接使用函数，不继承 BaseView）
async def export_opml(request: Request):
    """导出OPML文件"""
    session = db.get_session()
    try:
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

        # 直接返回 XML 内容，不触发下载
        return Response(
            content=xml_string,
            media_type="application/xml; charset=utf-8"
        )
    finally:
        session.close()

async def import_opml(request: Request):
    """导入OPML文件"""
    form = await request.form()
    file = form.get("file")

    if not file or not hasattr(file, 'filename'):
        return HTMLResponse(
            content='<html><body><h1>错误</h1><p>请选择OPML文件</p><a href="/admin/opml">返回</a></body></html>',
            status_code=400
        )

    if not file.filename.endswith('.opml'):
        return HTMLResponse(
            content='<html><body><h1>错误</h1><p>文件必须是OPML格式</p><a href="/admin/opml">返回</a></body></html>',
            status_code=400
        )

    session = db.get_session()
    try:
        # 读取文件内容
        content = await file.read()

        # 解析XML
        root = parse(io.BytesIO(content)).getroot()

        imported_count = 0
        skipped_count = 0
        errors = []

        def extract_outlines(element, parent_title=""):
            """递归提取所有outline元素"""
            outlines = []
            for child in element:
                if child.tag == "outline":
                    xml_url = child.get("xmlUrl") or child.get("xmlURL")
                    if xml_url:
                        outlines.append({
                            "url": xml_url,
                            "title": child.get("text") or child.get("title") or parent_title,
                            "html_url": child.get("htmlUrl") or child.get("htmlURL"),
                            "description": child.get("description")
                        })
                    child_title = child.get("text") or child.get("title") or parent_title
                    outlines.extend(extract_outlines(child, child_title))
            return outlines

        body = root.find("body")
        if body is None:
            return HTMLResponse(
                content='<html><body><h1>错误</h1><p>OPML文件格式错误：缺少body元素</p><a href="/admin/opml">返回</a></body></html>',
                status_code=400
            )

        outlines = extract_outlines(body)

        if not outlines:
            return HTMLResponse(
                content='<html><body><h1>错误</h1><p>OPML文件中没有找到RSS源</p><a href="/admin/opml">返回</a></body></html>',
                status_code=400
            )

        # 导入每个RSS源
        for outline in outlines:
            try:
                feed_url = outline["url"]
                existing = session.query(RSSFeed).filter(RSSFeed.url == feed_url).first()
                if existing:
                    skipped_count += 1
                    continue

                feed_record = await update_feed(session, feed_url)
                if feed_record:
                    imported_count += 1
                else:
                    errors.append(f"无法解析RSS源: {feed_url}")
            except Exception as e:
                errors.append(f"导入失败 {outline.get('url', '未知')}: {str(e)}")

        session.commit()

        # 生成结果页面
        error_html = ""
        if errors:
            error_html = f"<h3>错误 ({len(errors)} 个):</h3><ul>"
            for error in errors[:10]:  # 只显示前10个错误
                error_html += f"<li>{escape(error)}</li>"
            if len(errors) > 10:
                error_html += f"<li>...还有 {len(errors) - 10} 个错误</li>"
            error_html += "</ul>"

        result_html = f"""
        <html>
        <body>
            <h1>导入完成</h1>
            <p>成功导入: {imported_count} 个</p>
            <p>跳过: {skipped_count} 个</p>
            <p>总计: {len(outlines)} 个</p>
            {error_html}
            <p><a href="/admin/opml">返回OPML管理</a> | <a href="/admin/rssfeed">查看RSS源列表</a></p>
        </body>
        </html>
        """
        return HTMLResponse(content=result_html)
    except Exception as e:
        return HTMLResponse(
            content=f'<html><body><h1>错误</h1><p>解析OPML文件失败: {escape(str(e))}</p><a href="/admin/opml">返回</a></body></html>',
            status_code=400
        )
    finally:
        session.close()



# 创建 Admin 实例（需要在 main.py 中初始化）
def create_admin(app):
    """创建并配置管理面板"""
    authentication_backend = AdminAuth(secret_key=os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production"))
    admin = Admin(
        app=app,
        engine=db.engine,
        authentication_backend=authentication_backend,
        title="RSS Reader Admin",
        base_url="/admin",
    )

    # 注册视图
    admin.add_view(RSSFeedAdmin)
    admin.add_view(RSSItemAdmin)
    admin.add_view(UserAdmin)

    logger.info("SQLAdmin 管理面板已初始化，访问地址: /admin")

    return admin, authentication_backend
