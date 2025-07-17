#!/bin/bash

# 杀掉占用指定端口的进程
# 支持端口: 8000, 8100, 8200

echo "正在检查并杀掉占用端口 8000, 8100, 8200 的进程..."

# 定义端口数组
ports=(8000 8100 8200)

# 遍历每个端口
for port in "${ports[@]}"; do
    echo "检查端口 $port..."
    
    # 使用 lsof 查找占用端口的进程 PID
    pid=$(lsof -ti:$port)
    
    if [ -n "$pid" ]; then
        echo "发现端口 $port 被进程 $pid 占用，正在终止..."
        # 先尝试温和终止
        kill $pid
        sleep 2
        
        # 检查进程是否还在运行
        if kill -0 $pid 2>/dev/null; then
            echo "进程 $pid 仍在运行，强制终止..."
            kill -9 $pid
        fi
        
        echo "端口 $port 上的进程已终止"
    else
        echo "端口 $port 未被占用"
    fi
done

echo "端口清理完成！"
