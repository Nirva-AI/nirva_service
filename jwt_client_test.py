import requests
from typing import Final, Optional, Dict, cast, Any
from config.user_account import FAKE_USER
from config.configuration import MKCERT_ROOT_CA, LOCAL_HTTPS_ENABLED

# 服务器地址
BASE_URL: Final[str] = (
    LOCAL_HTTPS_ENABLED and "https://localhost:8000" or "http://localhost:8000"
)


class ApiClient:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None

    def login(self, username: str, password: str) -> bool:
        """登录并获取初始令牌"""
        response = requests.post(
            f"{self.base_url}/token",
            data={"username": username, "password": password, "grant_type": "password"},
            verify=LOCAL_HTTPS_ENABLED and MKCERT_ROOT_CA or None,
        )

        if response.status_code == 200:
            data = response.json()
            self.access_token = data["access_token"]
            self.refresh_token = data["refresh_token"]
            return True
        return False

    def request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> requests.Response:
        """自动处理令牌刷新的请求方法"""
        headers = {}
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"

        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        response = requests.request(
            method,
            url,
            json=data,
            params=params,
            headers=headers,
            verify=LOCAL_HTTPS_ENABLED and MKCERT_ROOT_CA or None,
        )

        # 如果返回401且有刷新令牌，尝试刷新令牌并重试
        if response.status_code == 401 and self.refresh_token:
            if self._refresh_token():
                # 更新令牌并重试请求
                headers["Authorization"] = f"Bearer {self.access_token}"
                response = requests.request(
                    method,
                    url,
                    json=data,
                    params=params,
                    headers=headers,
                    verify=LOCAL_HTTPS_ENABLED and MKCERT_ROOT_CA or None,
                )

        return response

    def _refresh_token(self) -> bool:
        """刷新访问令牌"""
        if not self.refresh_token:
            return False

        response = requests.post(
            f"{self.base_url}/refresh-token",
            json={"refresh_token": self.refresh_token},
            verify=LOCAL_HTTPS_ENABLED and MKCERT_ROOT_CA or None,
        )

        if response.status_code == 200:
            data = response.json()
            self.access_token = data["access_token"]
            self.refresh_token = data["refresh_token"]
            return True
        return False

    # 便捷方法
    def get(
        self, endpoint: str, params: Optional[Dict[str, Any]] = None
    ) -> requests.Response:
        return self.request("GET", endpoint, params=params)

    def post(
        self, endpoint: str, data: Optional[Dict[str, Any]] = None
    ) -> requests.Response:
        return self.request("POST", endpoint, data=data)

    # API方法示例
    def get_protected_data(self) -> Dict[str, Any]:
        """获取受保护数据的示例方法"""
        response = self.get("protected-data")
        if response.status_code == 200:
            return cast(Dict[str, Any], response.json())
        return {"error": f"访问失败: {response.status_code}"}


def main() -> None:
    client = ApiClient(BASE_URL)

    # 登录一次，后续所有请求自动维护令牌
    if client.login(FAKE_USER.username, "secret"):
        print("登录成功！")

        while True:
            user_input = input("请输入操作: /q 退出, /g 获取数据: ")

            if user_input == "/q":
                break

            elif user_input == "/g":
                # 简化的API调用，不需要手动处理令牌刷新
                data = client.get_protected_data()
                print("受保护数据:", data)


if __name__ == "__main__":
    main()
