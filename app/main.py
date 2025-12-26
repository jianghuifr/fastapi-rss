import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from starlette.middleware.sessions import SessionMiddleware
from pathlib import Path
from loguru import logger
from app.routes import router, auth_router
from app.admin import create_admin
from app.database import db
from app.auth import init_default_admin

# 配置 loguru
logger.remove()  # 移除默认的处理器
logger.add(
    lambda msg: print(msg, end=""),  # 输出到标准输出
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="INFO"
)

app = FastAPI(
    title="RSS Reader",
    description="RSS Reader",
    version="0.1.0"
)

# Session 中间件（sqladmin 需要）
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
)

# CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 初始化管理面板（必须在所有路由之前，确保 /admin 路由优先注册）
admin, authentication_backend = create_admin(app)

# 注册 OPML 管理路由（必须在 sqladmin 初始化之后，但在其他路由之前）
from app.admin import export_opml, import_opml
from fastapi import Request
from fastapi.responses import HTMLResponse, RedirectResponse

@app.get("/admin/opml")
async def opml_page(request: Request):
    """OPML管理页面"""
    if not await authentication_backend.authenticate(request):
        return RedirectResponse(url="/admin/login")

    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>OPML管理 - RSS Reader Admin</title>
        <meta charset="UTF-8">
        <style>
            body { font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; }
            h1 { color: #333; }
            .section { margin: 30px 0; padding: 20px; border: 1px solid #ddd; border-radius: 5px; }
            .btn { display: inline-block; padding: 10px 20px; background: #007bff; color: white; text-decoration: none; border-radius: 3px; margin: 10px 5px; }
            .btn:hover { background: #0056b3; }
            .btn-secondary { background: #6c757d; }
            .btn-secondary:hover { background: #545b62; }
            form { margin: 20px 0; }
            input[type="file"] { margin: 10px 0; }
            .back-link { margin-top: 20px; }
        </style>
    </head>
    <body>
        <h1>OPML管理</h1>

        <div class="section">
            <h2>导出OPML</h2>
            <p>将当前所有RSS源导出为OPML文件</p>
            <a href="/admin/opml/export" class="btn">导出OPML</a>
        </div>

        <div class="section">
            <h2>导入OPML</h2>
            <p>从OPML文件导入RSS源</p>
            <form action="/admin/opml/import" method="post" enctype="multipart/form-data">
                <input type="file" name="file" accept=".opml" required>
                <br>
                <button type="submit" class="btn btn-secondary">导入OPML</button>
            </form>
        </div>

        <div class="back-link">
            <a href="/admin">返回管理面板</a>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.get("/admin/opml/export")
async def opml_export_route(request: Request):
    """导出OPML"""
    if not await authentication_backend.authenticate(request):
        return RedirectResponse(url="/admin/login")
    return await export_opml(request)

@app.post("/admin/opml/import")
async def opml_import_route(request: Request):
    """导入OPML"""
    if not await authentication_backend.authenticate(request):
        return RedirectResponse(url="/admin/login")
    return await import_opml(request)

# 注册路由（在管理面板之后注册）
app.include_router(router)
app.include_router(auth_router)

# 初始化默认管理员账户
@app.on_event("startup")
def startup_event():
    session = db.get_session()
    try:
        init_default_admin(session)
    finally:
        session.close()

# 静态文件服务（前端构建后的文件）
# 注意：这个 catch-all 路由必须在最后注册，避免拦截管理面板路由
frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"
frontend_src = Path(__file__).parent.parent / "frontend"
if frontend_dist.exists():
    # 静态资源文件
    assets_dir = frontend_dist / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    # Favicon 路由（优先从构建目录查找，如果不存在则从源码目录查找）
    @app.get("/favicon.svg")
    async def favicon():
        """Favicon图标"""
        favicon_path = frontend_dist / "favicon.svg"
        if not favicon_path.exists():
            favicon_path = frontend_src / "favicon.svg"
        if favicon_path.exists():
            return FileResponse(str(favicon_path), media_type="image/svg+xml")
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Favicon not found")

    # 服务前端页面（SPA路由）
    # 注意：FastAPI 的路由匹配机制中，catch-all 路由会匹配所有路径
    # 如果 catch-all 路由匹配了，即使抛出异常也不会继续查找其他路由
    # 解决方案：使用中间件在路由匹配前检查，或者使用更精确的路由匹配
    # 这里我们暂时注释掉 catch-all 路由，让 sqladmin 先工作
    # 如果需要前端 SPA 路由，可以使用中间件或者更精确的路由匹配

    # 暂时注释掉，测试 sqladmin 是否工作
    # @app.get("/{path:path}")
    # async def serve_frontend(path: str):
    #     """服务前端页面"""
    #     excluded_prefixes = ["api", "docs", "openapi.json", "redoc", "health", "admin"]
    #     if any(path.startswith(prefix) for prefix in excluded_prefixes):
    #         from fastapi import HTTPException
    #         raise HTTPException(status_code=404, detail="Not found")
    #     index_file = frontend_dist / "index.html"
    #     if index_file.exists():
    #         return FileResponse(str(index_file))
    #     return {"message": "Frontend not built"}


@app.get("/")
def root():
    """根路径"""
    # 如果前端已构建，重定向到前端
    index_file = frontend_dist / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return {
        "message": "RSS Reader",
        "docs": "/docs",
        "version": "0.1.0"
    }


@app.get("/health")
def health_check():
    """健康检查"""
    return {"status": "healthy"}
