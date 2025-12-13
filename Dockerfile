FROM python:3.13-slim
LABEL maintainer=jianghuifr@outlook.com

ENV TZ=Asia/Shanghai
ENV LANG=C.UTF-8

WORKDIR /app
COPY app .
RUN uv sync --frozen --no-install-project

COPY docker-entrypoint.sh /docker-entrypoint.sh
CMD ["/docker-entrypoint.sh", "--app"]
# CMD ["/docker-entrypoint.sh", "--worker"]
