import asyncio
import time
from typing import Any, Dict, Final, List, final

import httpx
from loguru import logger

from .langgraph_request_task import LanggraphRequestTask


@final
class LanggraphService:
    ################################################################################################################################################################################
    def __init__(
        self,
        chat_service_localhost_urls: List[str],
        chat_service_test_get_urls: List[str],
        analyzer_service_localhost_urls: List[str],
        analyzer_service_test_get_urls: List[str],
    ) -> None:
        # 异步请求客户端
        self._async_client: Final[httpx.AsyncClient] = httpx.AsyncClient()

        # 聊天服务的 URL
        self._chat_service_localhost_urls: Final[
            List[str]
        ] = chat_service_localhost_urls
        self._chat_service_request_distribution_index: int = 0
        # 聊天服务的测试 GET URL
        self._chat_service_test_get_urls: Final[List[str]] = chat_service_test_get_urls

        # 分析服务的 URL
        self._analyzer_service_localhost_urls: Final[
            List[str]
        ] = analyzer_service_localhost_urls
        self._analyzer_service_request_distribution_index: int = 0
        # 分析服务的测试 GET URL
        self._analyzer_service_test_get_urls: Final[
            List[str]
        ] = analyzer_service_test_get_urls

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
            request_distribution_index=self._analyzer_service_request_distribution_index,
        )
        self._analyzer_service_request_distribution_index += len(request_handlers)

    ################################################################################################################################################################################
    async def check_services_health(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        检查聊天服务和分析服务的健康状态

        Returns:
            Dict[str, List[Dict[str, Any]]]: 包含每个服务所有端点健康状态的字典
        """
        chat_services_status = []
        analyzer_services_status = []

        # 检查聊天服务
        for url in self._chat_service_test_get_urls:
            try:
                start_time = time.time()
                response = await self._async_client.get(url)
                end_time = time.time()

                if response.status_code == 200:
                    status_info = {
                        "url": url,
                        "status": "healthy",
                        "response_time": f"{(end_time - start_time):.2f}s",
                        "details": response.json(),
                    }
                else:
                    status_info = {
                        "url": url,
                        "status": "unhealthy",
                        "response_time": f"{(end_time - start_time):.2f}s",
                        "error": f"状态码: {response.status_code}",
                    }
            except Exception as e:
                status_info = {"url": url, "status": "unreachable", "error": str(e)}

            chat_services_status.append(status_info)
            logger.debug(f"Chat服务健康检查 {url}: {status_info['status']}")

        # 检查分析服务
        for url in self._analyzer_service_test_get_urls:
            try:
                start_time = time.time()
                response = await self._async_client.get(url)
                end_time = time.time()

                if response.status_code == 200:
                    status_info = {
                        "url": url,
                        "status": "healthy",
                        "response_time": f"{(end_time - start_time):.2f}s",
                        "details": response.json(),
                    }
                else:
                    status_info = {
                        "url": url,
                        "status": "unhealthy",
                        "response_time": f"{(end_time - start_time):.2f}s",
                        "error": f"状态码: {response.status_code}",
                    }
            except Exception as e:
                status_info = {"url": url, "status": "unreachable", "error": str(e)}

            analyzer_services_status.append(status_info)
            logger.debug(f"分析服务健康检查 {url}: {status_info['status']}")

        return {
            "chat_services": chat_services_status,
            "analyzer_services": analyzer_services_status,
        }

    ################################################################################################################################################################################
