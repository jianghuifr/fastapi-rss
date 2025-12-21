"""FastAPI主应用"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
from app.routes import router

app = FastAPI(
    title="RSS订阅服务",
    description="RSS订阅服务端，支持定时轮询更新",
    version="0.1.0"
)

# CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(router)

# 静态文件服务（前端构建后的文件）
frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"
if frontend_dist.exists():
    # 静态资源文件
    assets_dir = frontend_dist / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    # 服务前端页面（SPA路由）
    @app.get("/{path:path}")
    async def serve_frontend(path: str):
        """服务前端页面"""
        # API 和文档路径直接返回 None，让 FastAPI 处理
        if path.startswith("api") or path.startswith("docs") or path.startswith("openapi.json") or path.startswith("redoc"):
            return None
        index_file = frontend_dist / "index.html"
        if index_file.exists():
            return FileResponse(str(index_file))
        return {"message": "Frontend not built"}


@app.get("/")
def root():
    """根路径"""
    # 如果前端已构建，重定向到前端
    index_file = frontend_dist / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return {
        "message": "RSS订阅服务",
        "docs": "/docs",
        "version": "0.1.0"
    }


@app.get("/health")
def health_check():
    """健康检查"""
    return {"status": "healthy"}
