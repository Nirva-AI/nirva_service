from loguru import logger
from typing import Final, List, Any, final
import httpx
import asyncio
import time
from langgraph_services.langgraph_request_task import LanggraphRequestTask


@final
class LanggraphService:

    ################################################################################################################################################################################
    def __init__(
        self,
        chat_service_localhost_urls: List[str],
        analyzer_service_localhost_urls: List[str],
    ) -> None:

        # 异步请求客户端
        self._async_client: Final[httpx.AsyncClient] = httpx.AsyncClient()

        # 运行的服务器
        assert len(chat_service_localhost_urls) > 0
        self._chat_service_localhost_urls: Final[List[str]] = (
            chat_service_localhost_urls
        )

        # 不同的请求分配到不同的 URL
        self._chat_service_request_distribution_index: int = 0

        # 分析服务的 URL
        self._analyzer_service_localhost_urls: Final[List[str]] = (
            analyzer_service_localhost_urls
        )

    ################################################################################################################################################################################
    async def gather(
        self, request_handlers: List[LanggraphRequestTask], urls: List[str]
    ) -> List[Any]:

        if len(request_handlers) == 0:
            return []

        if len(urls) == 0:
            return []

        coros = []
        for idx, handler in enumerate(request_handlers):
            # 循环复用
            endpoint_url = urls[idx % len(urls)]
            coros.append(handler.a_request(self._async_client, endpoint_url))

        # 允许异常捕获，不中断其他请求
        start_time = time.time()
        batch_results = await asyncio.gather(*coros, return_exceptions=True)
        end_time = time.time()
        logger.debug(f"LanggraphService.gather:{end_time - start_time:.2f} seconds")

        # 记录失败请求
        for result in batch_results:
            if isinstance(result, Exception):
                logger.error(f"Request failed: {result}")

        return batch_results

    ################################################################################################################################################################################
    def _handle(
        self,
        request_handlers: List[LanggraphRequestTask],
        urls: List[str],
        request_distribution_index: int,
    ) -> None:

        if len(request_handlers) == 0 or len(urls) == 0:
            return

        for idx, request_handler in enumerate(request_handlers):
            # 根据 self._handle_count 循环分配 URL
            endpoint_url = urls[(request_distribution_index + idx) % len(urls)]
            start_time = time.time()
            request_handler.request(endpoint_url)
            end_time = time.time()
            logger.debug(f"LanggraphService.handle:{end_time - start_time:.2f} seconds")

    ################################################################################################################################################################################
    def chat(self, request_handlers: List[LanggraphRequestTask]) -> None:
        self._handle(
            request_handlers=request_handlers,
            urls=self._chat_service_localhost_urls,
            request_distribution_index=self._chat_service_request_distribution_index,
        )
        # 更新
        self._chat_service_request_distribution_index += len(request_handlers)

    ################################################################################################################################################################################
    def analyze(self, request_handlers: List[LanggraphRequestTask]) -> None:
        self._handle(
            request_handlers=request_handlers,
            urls=self._analyzer_service_localhost_urls,
            request_distribution_index=0,
        )

    ################################################################################################################################################################################
