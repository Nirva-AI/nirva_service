#!/bin/bash

# 删除所有 pm2 进程
pm2 delete all

# 启动指定的 Python 脚本
pm2 start run_chat_server.py run_app_service_server.py