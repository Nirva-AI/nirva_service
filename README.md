# multi-agents-game-framework

## 依赖包安装

先安装anaconda或者miniconda。
Name 是环境的名（任取）。
如果用vscode 进行代码调试，需要用 >Python Interpreter. 将python环境指向这个Name代表的环境

```python
conda create -n Name python=3.12.2 
conda activate Name
pip install langchain langchain_core langserve langgraph fastapi langchain_openai sse_starlette faiss-cpu loguru mypy pandas openpyxl overrides Jinja2 jsonschema black pandas-stubs uvicorn "python-jose[cryptography]" passlib requests python-multipart bcrypt types-python-jose pip install types-passlib
```

## 需要特别注意

```shell
pip uninstall bcrypt -y
pip install bcrypt==3.2.2  # 已知兼容 passlib 1.7.4 的版本
```

## 严格模式检查

```shell
mypy --strict run_user_session_server.py simulator_client.py run_chat_server.py
mypy --strict jwt_server_test.py jwt_client_test.py
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
