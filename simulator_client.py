from typing import Any, Dict, Final, Union, cast, final
from loguru import logger
import requests
from models_v_0_0_1 import (
    URLConfigurationResponse,
    ChatActionRequest,
    ChatActionResponse,
)

from config.configuration import (
    GEN_CONFIGS_DIR,
    USER_SESSION_SERVER_CONFIG_PATH,
    UserSessionServerConfig,
    LOCAL_HTTPS_ENABLED,
    MKCERT_ROOT_CA,
)

from config.fake_user_account import fake_user_account
from db.jwt import Token


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
        password: str,
    ) -> None:

        self._server_ip_address: Final[str] = server_ip_address
        self._server_port: Final[int] = server_port
        self._user_name: Final[str] = user_name
        self._password: Final[str] = password
        self._url_configuration: URLConfigurationResponse = URLConfigurationResponse()
        self._token: Token = Token(
            access_token="",
            token_type="",
            refresh_token="",
        )

    ###########################################################################################################################
    @property
    def config_url(self) -> str:
        if LOCAL_HTTPS_ENABLED:
            return f"https://localhost:{self._server_port}/config"

        return f"http://{self._server_ip_address}:{self._server_port}/config"

    ###########################################################################################################################
    @property
    def login_url(self) -> str:
        return self._url_configuration.endpoints["login"]

    ###########################################################################################################################
    @property
    def chat_action_url(self) -> str:
        return self._url_configuration.endpoints["chat"]

    ###########################################################################################################################


###########################################################################################################################
def _post_request(
    url: str, data: Dict[str, Any], token: Token
) -> Union[Dict[str, Any], None]:

    logger.debug(f"_post_request url: {url}, data: {data}")

    response = requests.post(
        url=url,
        json=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token.access_token}",
        },
        verify=LOCAL_HTTPS_ENABLED and MKCERT_ROOT_CA or None,
    )

    if response.status_code == 200:
        response_data = response.json()
        logger.debug(f"_post_request reponse: {response_data}")
        return cast(Dict[str, Any], response_data)

    else:
        logger.error(f"Error: {response.status_code}, {response.text}")
    return None


###########################################################################################################################
async def _get_url_config(context: SimulatorContext) -> None:

    logger.debug(f"_get_request url: {context.config_url}")
    response = requests.get(
        context.config_url,
        headers={"Content-Type": "application/json"},
        verify=LOCAL_HTTPS_ENABLED and MKCERT_ROOT_CA or None,
    )

    if response.status_code == 200:

        context._url_configuration = URLConfigurationResponse.model_validate(
            response.json()
        )
        logger.info(f"url_config: {context._url_configuration.model_dump_json()}")

        # 生成配置文件, 写死先
        url_config_file_path = GEN_CONFIGS_DIR / "url_config.json"
        url_config_file_path.write_text(
            context._url_configuration.model_dump_json(),
            encoding="utf-8",
        )

    else:
        logger.error(f"Error: {response.status_code}, {response.text}")


###########################################################################################################################
async def _post_login(context: SimulatorContext) -> None:

    response = requests.post(
        context.login_url,
        data={
            "username": context._user_name,
            "password": context._password,
            "grant_type": "password",
        },
        verify=LOCAL_HTTPS_ENABLED and MKCERT_ROOT_CA or None,
    )

    if response.status_code == 200:
        context._token = Token.model_validate(response.json())
        logger.warning(f"登录成功！令牌已获取{context._token.model_dump_json()}")

    else:
        logger.warning("登录失败，请检查用户名和密码")


###########################################################################################################################
async def _handle_chat_action(context: SimulatorContext, user_input: str) -> None:

    content = _extract_user_input(user_input, "/chat")
    assert content != "", f"content: {content} is empty string."

    request_data = ChatActionRequest(content=content)
    response = _post_request(
        context.chat_action_url,
        data=request_data.model_dump(),
        token=context._token,
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
        user_name=fake_user_account.username,
        password="secret",  # 注意！！
    )

    # 直接开始。
    await _get_url_config(simulator_context)
    await _post_login(simulator_context)

    while True:
        try:
            user_input = input(f"[{simulator_context._user_name}]: ")
            if user_input.lower() in ["/quit", "/q"]:
                print("退出！")
                break

            if "/api" in user_input:
                await _get_url_config(simulator_context)
            elif "/login" in user_input:
                await _post_login(simulator_context)

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
