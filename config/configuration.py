from pydantic import BaseModel
from pathlib import Path


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
    server_ip_address: str = "127.0.0.1"
    server_port: int = 8000
    local_network_ip: str = "192.168.2.64"


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
# if not LLM_SERVER_CONFIG_PATH.exists():
llm_server_config = LLMServerConfig()
LLM_SERVER_CONFIG_PATH.write_text(
    llm_server_config.model_dump_json(),
    encoding="utf-8",
)

# 生成配置文件, 写死先
USER_SESSION_SERVER_CONFIG_PATH = GEN_CONFIGS_DIR / "user_session_server_config.json"
# if not USER_SESSION_SERVER_CONFIG_PATH.exists():
user_session_server_config = UserSessionServerConfig()
USER_SESSION_SERVER_CONFIG_PATH.write_text(
    user_session_server_config.model_dump_json(),
    encoding="utf-8",
)
