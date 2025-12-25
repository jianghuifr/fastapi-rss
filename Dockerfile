# 前端构建阶段
FROM node:20-alpine AS frontend-builder

WORKDIR /frontend

# 复制前端文件
COPY frontend/package.json ./
# 安装依赖
RUN yarn install

# 复制其他前端文件
COPY frontend ./
# 构建前端
RUN yarn build

# Python应用阶段
FROM python:3.13-slim
LABEL maintainer=jianghuifr@outlook.com

ENV TZ=Asia/Shanghai
ENV LANG=C.UTF-8

WORKDIR /app

# 复制项目文件
COPY pyproject.toml uv.lock ./
COPY app ./app
COPY worker ./worker

# 安装依赖
COPY --from=ghcr.io/astral-sh/uv:python3.13-alpine /usr/local/bin/uv /usr/local/bin/uvx /usr/local/bin/
RUN uv sync --frozen --no-install-project

# 从前端构建阶段复制构建产物
COPY --from=frontend-builder /frontend/dist ./frontend/dist

# 复制启动脚本
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

CMD ["/docker-entrypoint.sh", "--app"]
