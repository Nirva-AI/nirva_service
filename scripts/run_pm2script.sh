#!/bin/bash

# 删除所有 pm2 进程
pm2 delete all

./scripts/kill_ports.sh

# 启动指定的 Python 脚本
pm2 start scripts/run_chat_server.py scripts/run_analyzer_server.py scripts/run_appservice_server.py
