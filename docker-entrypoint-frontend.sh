#!/bin/sh
set -e

# 设置 yarn 镜像源
yarn config set registry https://registry.npmmirror.com

# 安装依赖（每次启动都检查并安装，确保依赖完整）
echo "检查并安装依赖..."
yarn install

# 验证 vite 是否可用
if ! yarn exec vite --version > /dev/null 2>&1; then
    echo "错误: vite 未找到，重新安装依赖..."
    rm -rf node_modules
    yarn install
fi

# 启动开发服务器（使用 yarn 直接运行 vite）
exec yarn dev --host 0.0.0.0
