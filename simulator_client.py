import datetime
from pathlib import Path
from typing import Any, Dict, Final, List, Union, cast, final, Optional, Tuple
import uuid
from loguru import logger
import requests
from models_v_0_0_1 import (
    URLConfigurationResponse,
    ChatActionRequest,
    ChatActionResponse,
    AnalyzeActionRequest,  # 添加这行
    AnalyzeActionResponse,  # 添加这行
    UploadTranscriptActionRequest,
    UploadTranscriptActionResponse,
    MessageRole,
    ChatMessage,
)

from config.configuration import (
    GEN_CONFIGS_DIR,
    AppserviceServerConfig,
    LOCAL_HTTPS_ENABLED,
    MKCERT_ROOT_CA,
    LOGS_DIR,
)

from config.account import FAKE_USER
from db.jwt import UserToken


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
        username: str,
        password: str,
        display_name: str,
    ) -> None:

        self._server_ip_address: Final[str] = server_ip_address
        self._server_port: Final[int] = server_port
        self._username: Final[str] = username
        self._password: Final[str] = password
        self._display_name: Final[str] = display_name
        self._url_configuration: URLConfigurationResponse = URLConfigurationResponse()
        self._token: UserToken = UserToken(
            access_token="",
            token_type="",
            refresh_token="",
        )
        self._chat_history: List[ChatMessage] = []

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
    @property
    def logout_url(self) -> str:
        return self._url_configuration.endpoints["logout"]

    ###########################################################################################################################
    @property
    def refresh_token_url(self) -> str:
        return self._url_configuration.endpoints["refresh"]

    ###########################################################################################################################
    @property
    def analyze_action_url(self) -> str:
        return self._url_configuration.endpoints["analyze"]

    ###########################################################################################################################
    @property
    def upload_transcript_url(self) -> str:
        return self._url_configuration.endpoints["upload_transcript"]

    ###########################################################################################################################


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
            "username": context._username,
            "password": context._password,
            "grant_type": "password",
        },
        verify=LOCAL_HTTPS_ENABLED and MKCERT_ROOT_CA or None,
    )

    if response.status_code == 200:
        context._token = UserToken.model_validate(response.json())
        logger.warning(f"登录成功！令牌已获取{context._token.model_dump_json()}")

    else:
        logger.warning("登录失败，请检查用户名和密码")


###########################################################################################################################
async def _post_logout(context: SimulatorContext) -> None:
    """处理用户登出请求"""
    # 1. 通知服务器使令牌失效
    response = requests.post(
        context.logout_url,
        headers={"Authorization": f"Bearer {context._token.access_token}"},
        verify=LOCAL_HTTPS_ENABLED and MKCERT_ROOT_CA or None,
    )

    if response.status_code == 200:
        logger.info("成功通知服务器登出")
    else:
        logger.warning(f"服务器登出通知失败: {response.status_code}, {response.text}")

    # 2. 清除本地令牌
    context._token = UserToken(access_token="", token_type="", refresh_token="")
    logger.info("已清除本地令牌，用户登出成功")


###########################################################################################################################
def _refresh_token(context: SimulatorContext) -> bool:
    """刷新访问令牌"""
    if context._token.refresh_token == "":
        logger.error("没有可用的刷新令牌，无法刷新访问令牌。")
        return False

    response = requests.post(
        context.refresh_token_url,
        json={"refresh_token": context._token.refresh_token},
        verify=LOCAL_HTTPS_ENABLED and MKCERT_ROOT_CA or None,
    )

    if response.status_code == 200:
        data = response.json()
        context._token.access_token = data["access_token"]
        context._token.refresh_token = data["refresh_token"]
        return True
    return False


###########################################################################################################################
def _safe_post(
    url: str, data: Dict[str, Any], context: SimulatorContext
) -> Union[Dict[str, Any], None]:
    """发送POST请求，自动处理令牌刷新"""

    logger.debug(f"_post_request url: {url}, data: {data}")

    # 初始请求
    response = requests.post(
        url=url,
        json=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {context._token.access_token}",
        },
        verify=LOCAL_HTTPS_ENABLED and MKCERT_ROOT_CA or None,
        timeout=60,  # 设置超时时间为60秒
    )

    # 处理令牌过期情况 (401状态码)
    if response.status_code == 401 and context._token.refresh_token:
        logger.info("令牌已过期，尝试刷新...")

        # 尝试刷新令牌
        refresh_success = _refresh_token(context)

        if refresh_success:
            logger.info("令牌刷新成功，重新尝试请求")
            # 使用新令牌重新发送请求
            response = requests.post(
                url=url,
                json=data,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {context._token.access_token}",
                },
                verify=LOCAL_HTTPS_ENABLED and MKCERT_ROOT_CA or None,
            )
        else:
            logger.error("令牌刷新失败")

    # 处理最终的响应结果
    if response.status_code == 200:
        response_data = response.json()
        logger.debug(f"_post_request response: {response_data}")
        return cast(Dict[str, Any], response_data)
    else:
        logger.error(f"请求失败: {response.status_code}, {response.text}")
        return None


###########################################################################################################################
def _safe_get(
    url: str,
    context: SimulatorContext,
    params: Optional[Dict[str, Any]] = None,
) -> Union[Dict[str, Any], None]:
    """发送GET请求，自动处理令牌刷新

    Args:
        url: 请求的URL
        params: URL查询参数
        context: 包含认证令牌的上下文

    Returns:
        解析后的JSON响应或None（如果请求失败）
    """

    logger.debug(f"_safe_get url: {url}, params: {params}")

    # 初始请求
    response = requests.get(
        url=url,
        params=params,
        headers={
            "Authorization": f"Bearer {context._token.access_token}" if context else "",
        },
        verify=LOCAL_HTTPS_ENABLED and MKCERT_ROOT_CA or None,
    )

    # 处理令牌过期情况 (401状态码)
    if response.status_code == 401 and context and context._token.refresh_token:
        logger.info("令牌已过期，尝试刷新...")

        # 尝试刷新令牌
        refresh_success = _refresh_token(context)

        if refresh_success:
            logger.info("令牌刷新成功，重新尝试请求")
            # 使用新令牌重新发送请求
            response = requests.get(
                url=url,
                params=params,
                headers={
                    "Authorization": f"Bearer {context._token.access_token}",
                },
                verify=LOCAL_HTTPS_ENABLED and MKCERT_ROOT_CA or None,
            )
        else:
            logger.error("令牌刷新失败")

    # 处理最终的响应结果
    if response.status_code == 200:
        try:
            response_data = response.json()
            logger.debug(f"_safe_get response: {response_data}")
            return cast(Dict[str, Any], response_data)
        except ValueError:
            # 处理响应不是JSON的情况
            logger.warning("响应不是有效的JSON格式")
            return None
    else:
        logger.error(f"请求失败: {response.status_code}, {response.text}")
        return None


###########################################################################################################################
async def _post_chat_action(context: SimulatorContext, user_input: str) -> None:

    content = _extract_user_input(user_input, "/chat")
    assert content != "", f"content: {content} is empty string."

    request_data = ChatActionRequest(
        human_message=ChatMessage(
            id=str(uuid.uuid4()),
            role=MessageRole.HUMAN,
            content=content,
            time_stamp=datetime.datetime.now().isoformat(),
        ),
        chat_history=context._chat_history,
    )

    response = _safe_post(
        context.chat_action_url,
        data=request_data.model_dump(),
        context=context,  # 传递整个context而不仅仅是token
    )
    if response is not None:
        response_model = ChatActionResponse.model_validate(response)
        logger.info(f"_handle_chat_action: {response_model.model_dump_json()}")

        ## 更新聊天历史
        context._chat_history.append(request_data.human_message)
        context._chat_history.append(response_model.ai_message)


###########################################################################################################################
async def _post_analyze_action(context: SimulatorContext, user_input: str) -> None:
    """处理分析请求，发送到服务器进行分析"""

    upload_file = _extract_user_input(user_input, "/analyze")
    assert upload_file != "", f"content: {upload_file} is empty string."

    invisible_path = Path("invisible") / upload_file
    assert invisible_path.exists(), f"Log path does not exist: {invisible_path}"
    if not invisible_path.exists():
        logger.error(f"Log path does not exist: {invisible_path}")
        return

    transcript_content = invisible_path.read_text(encoding="utf-8").strip()
    assert transcript_content != "", "转录内容不能为空"

    parse_info = _parse_data_from_special_filename(upload_file)
    if parse_info is None:
        logger.error(f"无法从文件名 {upload_file} 中解析出日期时间、文件编号或后缀。")
        return

    request_data = AnalyzeActionRequest(
        time_stamp=parse_info[0].isoformat(),
        file_number=parse_info[1],
    )
    response = _safe_post(
        context.analyze_action_url,
        data=request_data.model_dump(),
        context=context,  # 传递整个context而不仅仅是token
    )

    if response is not None:
        response_model = AnalyzeActionResponse.model_validate(response)
        logger.info(f"_handle_analyze_action: {response_model.model_dump_json()}")

        # LOGS_DIR
        log_file_path = LOGS_DIR / f"analyze_result_{upload_file}.json"
        log_file_path.write_text(
            response_model.journal_file.model_dump_json(),
            encoding="utf-8",
        )


###########################################################################################################################
def _parse_data_from_special_filename(
    filename: str,
) -> Optional[Tuple[datetime.datetime, int, str]]:
    """从文件名中提取日期时间字符串、文件编号和后缀"""

    # 从这种文件名字为 ‘nirva-2025-04-19-00.txt’，提取日期时间字符串2025, 04, 19。后缀为txt, file_number为0
    parts = filename.split("-")
    if len(parts) < 5:
        logger.error(f"文件名格式不正确: {filename}")
        return None

    # 检查文件名的前缀是否为 "nirva"
    if parts[0] != "nirva":
        logger.error(f"文件名不符合预期格式: {filename}")
        return None

    try:
        year = int(parts[1])
        month = int(parts[2])
        day = int(parts[3])
        file_number = int(parts[4].split(".")[0])  # 提取文件编号
        file_suffix = parts[4].split(".")[-1]  # 提取文件后缀

        # 创建日期时间对象
        date_time = datetime.datetime(year, month, day)
        return date_time, file_number, file_suffix
    except ValueError as e:
        logger.error(f"解析文件名时出错: {e}, 文件名: {filename}")
        # 如果解析失败，返回None
        logger.error(f"无法从文件名 {filename} 中解析出日期时间、文件编号或后缀。")

    return None


###########################################################################################################################
async def _post_upload_transcript_action(
    context: SimulatorContext, user_input: str
) -> None:
    """处理分析请求，发送到服务器进行分析"""

    upload_file = _extract_user_input(user_input, "/upload_transcript")
    assert upload_file != "", f"content: {upload_file} is empty string."

    invisible_path = Path("invisible") / upload_file
    assert invisible_path.exists(), f"Log path does not exist: {invisible_path}"
    if not invisible_path.exists():
        logger.error(f"Log path does not exist: {invisible_path}")
        return

    transcript_content = invisible_path.read_text(encoding="utf-8").strip()
    assert transcript_content != "", "转录内容不能为空"

    parse_info = _parse_data_from_special_filename(upload_file)
    if parse_info is None:
        logger.error(f"无法从文件名 {upload_file} 中解析出日期时间、文件编号或后缀。")
        return

    request_data = UploadTranscriptActionRequest(
        transcript_content=transcript_content,
        time_stamp=parse_info[0].isoformat(),
        file_number=parse_info[1],
        file_suffix=parse_info[2],
    )
    response = _safe_post(
        context.upload_transcript_url,
        data=request_data.model_dump(),
        context=context,  # 传递整个context而不仅仅是token
    )
    if response is not None:
        response_model = UploadTranscriptActionResponse.model_validate(response)
        logger.info(
            f"_post_upload_transcript_action: {response_model.model_dump_json()}"
        )


###########################################################################################################################


###########################################################################################################################
async def _simulator() -> None:

    appservice_server_config = AppserviceServerConfig()

    simulator_context = SimulatorContext(
        server_ip_address=appservice_server_config.server_ip_address == "0.0.0.0"
        and appservice_server_config.local_network_ip
        or appservice_server_config.server_ip_address,
        server_port=appservice_server_config.server_port,
        username=FAKE_USER.username,
        password="secret",  # 注意！！
        display_name=FAKE_USER.display_name,
    )

    # 直接开始。
    await _get_url_config(simulator_context)
    await _post_login(simulator_context)

    while True:
        try:
            user_input = input(f"[{simulator_context._display_name}]: ")
            if user_input.lower() in ["/quit", "/q"]:
                print("退出！")
                break

            if "/config" in user_input:
                await _get_url_config(simulator_context)
            elif "/login" in user_input:
                await _post_login(simulator_context)
            elif "/logout" in user_input:
                await _post_logout(simulator_context)
            elif "/chat" in user_input:
                await _post_chat_action(simulator_context, user_input)
            elif "/analyze" in user_input:  # 添加这行
                # /analyze nirva-2025-04-19-00.txt
                # /analyze nirva-2025-05-09-00.txt
                await _post_analyze_action(simulator_context, user_input)

            elif "/upload_transcript" in user_input:
                # /upload_transcript nirva-2025-04-19-00.txt
                # /upload_transcript nirva-2025-05-09-00.txt
                copy_user_input = str(user_input)
                await _post_upload_transcript_action(simulator_context, user_input)
                copy_user_input = copy_user_input.replace(
                    "/upload_transcript", "/analyze"
                )
                await _post_analyze_action(simulator_context, copy_user_input)

            else:
                logger.info(f"Unknown command: {user_input}")

        except Exception as e:
            logger.error(f"Exception: {e}")

    ## 结束了
    logger.info("Simulate client exit!")


###########################################################################################################################
async def main() -> None:
    await _simulator()


###########################################################################################################################

if __name__ == "__main__":

    import asyncio

    asyncio.run(main())
