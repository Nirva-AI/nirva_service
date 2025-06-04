# multi-agents-game-framework

## 依赖包安装

先安装anaconda或者miniconda。
Name 是环境的名（任取）。
如果用vscode 进行代码调试，需要用 >Python Interpreter. 将python环境指向这个Name代表的环境

```python
conda create -n Name python=3.12.2 
conda activate Name
pip install langchain langchain_core langserve langgraph fastapi langchain_openai sse_starlette faiss-cpu loguru mypy pandas openpyxl overrides Jinja2 jsonschema black pandas-stubs uvicorn "python-jose[cryptography]" passlib requests python-multipart bcrypt types-python-jose sqlalchemy2-stubs types-passlib sqlalchemy asyncpg psycopg2 types-redis
```

## 需要特别注意

```shell
pip uninstall bcrypt -y
pip install bcrypt==3.2.2  # 已知兼容 passlib 1.7.4 的版本
```

## 严格模式检查

```shell
mypy --strict run_appservice_server.py simulator_client.py run_chat_server.py run_analyzer_server.py run_clear_db.py run_test_db.py
mypy --strict  jwt_server_test.py jwt_client_test.py
```

## 用pm2 批量启动 chat_server + appservice_server

```shell
./run_pm2script.sh
```

## 升级langchain

```shell
pip install --upgrade langchain langchain_core langserve langchain_openai langchain-community 
pip show langchain langchain_core langserve langchain_openai langchain-community
```

## 自动化测试 (安装)

```shell
conda install pytest
```

## 简单授权/身份验证 + JWT 的 demo

- jwt_client_test.py
- jwt_server_test.py

## 安装 redis 和 fastapi-redis-cache

```shell
conda install -c conda-forge redis pyhumps
# 或
pip install redis fastapi-redis-cache
```

## 注意conda环境

conda env export > environment.yml
