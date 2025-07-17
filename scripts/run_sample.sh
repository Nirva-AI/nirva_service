#!/bin/bash

# 切换到项目根目录
cd "$(dirname "$0")/.."

echo "启动微服务架构..."
echo "内部服务: http://192.168.192.104:8100"
echo "主服务: http://192.168.192.104:8000"
echo "主服务API文档: http://192.168.192.104:8000/docs"
echo "按 Ctrl+C 停止所有服务"
echo "----------------------------------------"

# 启动内部服务（后台运行）
echo "启动内部服务 (端口 8100)..."
uvicorn scripts.run_sample_internal_service:app --host 0.0.0.0 --port 8100 &
INTERNAL_PID=$!

# 等待内部服务启动
sleep 3

# 启动主服务（前台运行）
echo "启动主服务 (端口 8000)..."
uvicorn scripts.run_sample_app:app --host 0.0.0.0 --port 8000

# 清理：当主服务停止时，也停止内部服务
echo "正在停止内部服务..."
kill $INTERNAL_PID 2>/dev/null