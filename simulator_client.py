from typing import Any, Dict, Final, Union, cast, final
from loguru import logger
import requests
from models_v_0_0_1 import (
    URLConfigurationResponse,
    LoginRequest,
    LoginResponse,
    LogoutRequest,
    LogoutResponse,
    ChatActionRequest,
    ChatActionResponse,
)

from config.configuration import (
    GEN_CONFIGS_DIR,
    USER_SESSION_SERVER_CONFIG_PATH,
    UserSessionServerConfig,
)

from config.test_user_account import simu_test_user_account


###########################################################################################################################
def _extract_user_input(user_input: str, symbol: str) -> str:
    assert symbol in user_input, f"symbol: {symbol} not in user_input: {user_input}"
    assert symbol != "", f"symbol: {symbol} is empty string."
    # 先去掉前面的空格。
    user_input = user_input.strip()
    if not user_input.startswith(symbol):
        return user_input

    user_input = user_input[len(symbol) :].strip()
    return user_input


###########################################################################################################################
###########################################################################################################################
###########################################################################################################################
@final
class SimulatorContext:

    def __init__(
        self,
        server_ip_address: str,
        server_port: int,
        user_name: str,
    ) -> None:

        self._server_ip_address: Final[str] = server_ip_address
        self._server_port: Final[int] = server_port
        self._user_name: Final[str] = user_name
        self._url_configuration: URLConfigurationResponse = URLConfigurationResponse()

    ###########################################################################################################################
    @property
    def config_url(self) -> str:
        return f"http://{self._server_ip_address}:{self._server_port}/config"

    ###########################################################################################################################
    @property
    def login_url(self) -> str:
        return self._url_configuration.endpoints["login"]

    ###########################################################################################################################
    @property
    def logout_url(self) -> str:
        return self._url_configuration.endpoints["logout"]

    ###########################################################################################################################
    @property
    def chat_action_url(self) -> str:
        return self._url_configuration.endpoints["chat"]


###########################################################################################################################
def _post_request(
    url: str,
    data: Dict[str, Any],
) -> Union[Dict[str, Any], None]:

    logger.debug(f"_post_request url: {url}, data: {data}")
    response = requests.post(
        url,
        json=data,
        headers={"Content-Type": "application/json"},
    )

    if response.status_code == 200:
        response_data = response.json()
        logger.debug(f"_post_request reponse: {response_data}")
        return cast(Dict[str, Any], response_data)

    else:
        logger.error(f"Error: {response.status_code}, {response.text}")
    return None


###########################################################################################################################
def _get_request(
    url: str,
) -> Union[Dict[str, Any], None]:

    logger.debug(f"_get_request url: {url}")
    response = requests.get(
        url,
        headers={"Content-Type": "application/json"},
    )

    if response.status_code == 200:
        response_data = response.json()
        logger.debug(f"_get_request reponse: {response_data}")
        return cast(Dict[str, Any], response_data)

    else:
        logger.error(f"Error: {response.status_code}, {response.text}")
    return None


###########################################################################################################################
async def _handle_url_config(context: SimulatorContext) -> None:
    response = _get_request(
        context.config_url,
    )
    if response is not None:
        context._url_configuration = URLConfigurationResponse.model_validate(response)
        logger.info(f"api_endpoints: {context._url_configuration.model_dump_json()}")

        # 生成配置文件, 写死先
        url_config_file_path = GEN_CONFIGS_DIR / "url_config.json"
        url_config_file_path.write_text(
            context._url_configuration.model_dump_json(),
            encoding="utf-8",
        )


###########################################################################################################################
async def _handle_login(context: SimulatorContext) -> None:
    request_data = LoginRequest(user_name=context._user_name)
    response = _post_request(
        context.login_url,
        data=request_data.model_dump(),
    )
    if response is not None:
        response_model = LoginResponse.model_validate(response)
        logger.info(f"login: {response_model.model_dump_json()}")


###########################################################################################################################
async def _handle_logout(context: SimulatorContext) -> None:
    request_data = LogoutRequest(user_name=context._user_name)
    response = _post_request(
        context.logout_url,
        data=request_data.model_dump(),
    )
    if response is not None:
        response_model = LogoutResponse.model_validate(response)
        logger.info(f"logout: {response_model.model_dump_json()}")


###########################################################################################################################
async def _handle_chat_action(context: SimulatorContext, user_input: str) -> None:

    content = _extract_user_input(user_input, "/chat")
    assert content != "", f"content: {content} is empty string."

    request_data = ChatActionRequest(user_name=context._user_name, content=content)
    response = _post_request(
        context.chat_action_url,
        data=request_data.model_dump(),
    )
    if response is not None:
        response_model = ChatActionResponse.model_validate(response)
        logger.info(f"_handle_chat_action: {response_model.model_dump_json()}")


###########################################################################################################################
async def _simulator() -> None:

    assert (
        USER_SESSION_SERVER_CONFIG_PATH.exists()
    ), f"找不到配置文件: {USER_SESSION_SERVER_CONFIG_PATH}"
    config_file_content = USER_SESSION_SERVER_CONFIG_PATH.read_text(encoding="utf-8")
    user_session_server_config = UserSessionServerConfig.model_validate_json(
        config_file_content
    )

    simulator_context = SimulatorContext(
        server_ip_address=user_session_server_config.server_ip_address == "0.0.0.0"
        and user_session_server_config.local_network_ip
        or user_session_server_config.server_ip_address,
        server_port=user_session_server_config.server_port,
        user_name=simu_test_user_account.username,
    )

    # 直接开始。
    await _handle_url_config(simulator_context)
    await _handle_login(simulator_context)

    while True:
        try:
            user_input = input(f"[{simulator_context._user_name}]: ")
            if user_input.lower() in ["/quit", "/q"]:
                print("退出！")
                break

            if "/api" in user_input:
                await _handle_url_config(simulator_context)
            elif "/login" in user_input:
                await _handle_login(simulator_context)
            elif "/logout" in user_input:
                await _handle_logout(simulator_context)
            elif "/chat" in user_input:
                await _handle_chat_action(simulator_context, user_input)
            else:
                logger.info(f"Unknown command: {user_input}")

        except Exception as e:
            logger.error(f"Exception: {e}")
            break

    ## 结束了
    logger.info("Simulate client exit!")


###########################################################################################################################
async def main() -> None:
    await _simulator()


###########################################################################################################################

if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
