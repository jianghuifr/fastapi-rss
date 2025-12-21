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
RUN pip install uv && uv sync --frozen --no-install-project

# 复制启动脚本
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

# 创建数据目录
RUN mkdir -p /app/data

CMD ["/docker-entrypoint.sh", "--app"]
