from pathlib import Path
from typing import List
from loguru import logger
import datetime
from dataclasses import dataclass
from llm_serves.service_config import (
    StartupConfiguration,
)

# 生成log的目录
LOGS_DIR: Path = Path("logs")
LOGS_DIR.mkdir(parents=True, exist_ok=True)
assert LOGS_DIR.exists(), f"找不到目录: {LOGS_DIR}"


###############################################################################################################################################
###############################################################################################################################################
###############################################################################################################################################
@dataclass
class UserSessionOptions:

    user: str

    ###############################################################################################################################################
    # 设置logger
    def setup_logger(self) -> None:
        assert self.user != ""
        log_dir = LOGS_DIR / self.user
        log_start_time = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        logger.add(log_dir / f"{log_start_time}.log", level="DEBUG")


###############################################################################################################################################
###############################################################################################################################################
###############################################################################################################################################
@dataclass
class ChatSystemOptions:
    user: str
    server_setup_config: str

    @property
    def localhost_urls(self) -> List[str]:

        config_file_path = Path(self.server_setup_config)
        assert config_file_path.exists()
        if not config_file_path.exists():
            logger.error(f"没有找到配置文件: {config_file_path}")
            return []

        try:

            ret: List[str] = []

            config_file_content = config_file_path.read_text(encoding="utf-8")
            agent_startup_config = StartupConfiguration.model_validate_json(
                config_file_content
            )

            for config in agent_startup_config.service_configurations:
                ret.append(f"http://localhost:{config.port}{config.api}")

            return ret

        except Exception as e:
            logger.error(f"Exception: {e}")

        return []


###############################################################################################################################################
