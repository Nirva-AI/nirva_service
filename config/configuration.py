from typing import Final
from pydantic import BaseModel
from pathlib import Path

"""
先都配置到这里写死了，简单点。
"""


##################################################################################################################
# 启动一个服务的配置
class LLMServerConfig(BaseModel):
    port: int = 8500
    temperature: float = 0.7
    api: str = "/v1/llm_serve/chat/"
    fast_api_title: str = "azure_chat_openai_gpt_4o_lang_graph"
    fast_api_version: str = "0.0.1"
    fast_api_description: str = (
        "一个Azure OpenAI的服务，使用LangGraph进行LLM服务，使用FastAPI进行服务化"
    )


##################################################################################################################
# 启动一个服务的配置
class UserSessionServerConfig(BaseModel):
    server_ip_address: str = "0.0.0.0"
    server_port: int = 8000
    local_network_ip: str = "192.168.22.108"


##################################################################################################################
# redis的配置
class RedisConfig(BaseModel):
    host: str = "localhost"
    port: int = 6379
    db: int = 0


##################################################################################################################


# 生成log的目录
LOGS_DIR: Path = Path("logs")
LOGS_DIR.mkdir(parents=True, exist_ok=True)
assert LOGS_DIR.exists(), f"找不到目录: {LOGS_DIR}"

# 根目录
GEN_CONFIGS_DIR: Path = Path("gen_configs")
GEN_CONFIGS_DIR.mkdir(parents=True, exist_ok=True)
assert GEN_CONFIGS_DIR.exists(), f"找不到目录: {GEN_CONFIGS_DIR}"


# 生成配置文件, 写死先
LLM_SERVER_CONFIG_PATH = GEN_CONFIGS_DIR / "llm_server_config.json"
llm_server_config = LLMServerConfig()
LLM_SERVER_CONFIG_PATH.write_text(
    llm_server_config.model_dump_json(),
    encoding="utf-8",
)

# 生成配置文件, 写死先
USER_SESSION_SERVER_CONFIG_PATH = GEN_CONFIGS_DIR / "user_session_server_config.json"
user_session_server_config = UserSessionServerConfig()
USER_SESSION_SERVER_CONFIG_PATH.write_text(
    user_session_server_config.model_dump_json(),
    encoding="utf-8",
)

# 生成RedisConfig配置文件，写死先
REDIS_CONFIG_PATH = GEN_CONFIGS_DIR / "redis_config.json"
redis_config = RedisConfig()
REDIS_CONFIG_PATH.write_text(
    redis_config.model_dump_json(),
    encoding="utf-8",
)

# mkcert 根证书路径
MKCERT_ROOT_CA: Final[str] = (
    r"/Users/yanghang/Library/Application Support/mkcert/rootCA.pem"
)

# 是否使用 HTTPS，默认是 True
LOCAL_HTTPS_ENABLED: Final[bool] = True  # 是否模拟使用 HTTPS，默认是 False
