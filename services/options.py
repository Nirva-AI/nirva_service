from loguru import logger
import datetime
from dataclasses import dataclass
from config.configuration import LOGS_DIR


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
