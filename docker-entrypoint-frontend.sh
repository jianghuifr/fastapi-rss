#!/bin/sh
set -e

yarn config set registry https://registry.npmmirror.com
yarn install
exec yarn dev
