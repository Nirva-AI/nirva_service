from typing import Any, Dict, Final, Union, cast, final
from loguru import logger
import requests
from models_v_0_0_1 import (
    APIEndpointConfiguration,
    APIEndpointConfigurationResponse,
    LoginRequest,
    LoginResponse,
    LogoutRequest,
    LogoutResponse,
    ChatActionRequest,
    ChatActionResponse,
)
import copy


###########################################################################################################################
def _extract_user_input(user_input: str, symbol: str) -> str:
    assert symbol in user_input, f"symbol: {symbol} not in user_input: {user_input}"
    assert symbol != "", f"symbol: {symbol} is empty string."
    # 先去掉前面的空格。
    user_input = user_input.strip()
    # 如果没有/chat，就直接返回。
    if not user_input.startswith(symbol):
        return user_input

    # 去掉/chat
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

        self._server_ip_address: Final[str] = server_ip_address  # "192.168.192.123"
        self._server_port: Final[int] = server_port  # 8000
        self._user_name: Final[str] = user_name  # "wei"
        self._api_endpoints_config: APIEndpointConfiguration = (
            APIEndpointConfiguration()
        )

    ###########################################################################################################################
    @property
    def api_endpoints_url(self) -> str:
        return f"http://{self._server_ip_address}:{self._server_port}/api_endpoints/v1/"


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
async def _handle_api_endpoints(context: SimulatorContext) -> None:
    response = _post_request(
        context.api_endpoints_url,
        data={},
    )
    if response is not None:
        response_model = APIEndpointConfigurationResponse.model_validate(response)
        context._api_endpoints_config = copy.copy(response_model.api_endpoints)
        logger.info(f"api_endpoints: {response_model.model_dump_json()}")


###########################################################################################################################
async def _handle_login(context: SimulatorContext) -> None:
    request_data = LoginRequest(user_name=context._user_name)
    response = _post_request(
        context._api_endpoints_config.LOGIN_URL,
        data=request_data.model_dump(),
    )
    if response is not None:
        response_model = LoginResponse.model_validate(response)
        logger.info(f"login: {response_model.model_dump_json()}")


###########################################################################################################################
async def _handle_logout(context: SimulatorContext) -> None:
    request_data = LogoutRequest(user_name=context._user_name)
    response = _post_request(
        context._api_endpoints_config.LOGOUT_URL,
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
        context._api_endpoints_config.CHAT_ACTION_URL,
        data=request_data.model_dump(),
    )
    if response is not None:
        response_model = ChatActionResponse.model_validate(response)
        logger.info(f"chat_action: {response_model.model_dump_json()}")


###########################################################################################################################
async def _simulator() -> None:

    simulator_context = SimulatorContext(
        server_ip_address="192.168.192.123",
        server_port=8000,
        user_name="wei",
    )

    # 直接开始。
    await _handle_api_endpoints(simulator_context)
    await _handle_login(simulator_context)

    while True:
        try:
            user_input = input(f"[{simulator_context._user_name}]: ")
            if user_input.lower() in ["/quit", "/q"]:
                print("退出！")
                break

            if "/api" in user_input:
                await _handle_api_endpoints(simulator_context)
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
