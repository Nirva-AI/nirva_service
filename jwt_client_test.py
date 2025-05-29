import requests
from typing import Final, Optional, Dict, cast
from jwt_server_test import ENABLE_HTTPS
from config.fake_user_account import fake_user_account

# 服务器地址
BASE_URL: Final[str] = (
    ENABLE_HTTPS and "https://localhost:8000" or "http://localhost:8000"
)

# mkcert 根证书路径
MKCERT_ROOT_CA: Final[str] = (
    r"/Users/yanghang/Library/Application Support/mkcert/rootCA.pem"
)


def login(username: str, password: str) -> Optional[str]:

    while username == "":
        username = input("请输入用户名: ")

    while password == "":
        password = input("请输入密码: ")

    response = requests.post(
        f"{BASE_URL}/token",
        data={"username": username, "password": password, "grant_type": "password"},
        verify=ENABLE_HTTPS and MKCERT_ROOT_CA or None,
        # MKCERT_ROOT_CA,  # 使用 mkcert 的根证书
    )

    if response.status_code == 200:
        token: str = response.json()["access_token"]
        print("登录成功！令牌已获取")
        return token
    else:
        print("登录失败，请检查用户名和密码")
        return None


def refresh_token(refresh_token: str) -> Optional[str]:
    response = requests.post(
        f"{BASE_URL}/refresh-token",
        json={"refresh_token": refresh_token},
        verify=ENABLE_HTTPS and MKCERT_ROOT_CA or None,
    )

    if response.status_code == 200:
        token: str = response.json()["access_token"]
        print("刷新令牌成功！新令牌已获取")
        return token
    else:
        print("刷新令牌失败，请重新登录")
        return None


def get_protected_data(token: str) -> Dict[str, str]:
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(
        f"{BASE_URL}/protected-data",
        headers=headers,
        verify=ENABLE_HTTPS and MKCERT_ROOT_CA or None,
        # MKCERT_ROOT_CA,  # 使用 mkcert 的根证书
    )

    if response.status_code == 200:
        return cast(Dict[str, str], response.json())
    else:
        return {"error": "访问失败"}


def main() -> None:
    # 测试流程
    token: Optional[str] = None  # 初始化 token
    refresh_token_value: Optional[str] = None  # 初始化 refresh_token
    while True:
        user_input = input(
            "请输入操作: /q 是退出, /a 是自动登录，/r 是重新登录: /g 是获取受保护数据: "
        )
        if user_input == "/q":
            print("退出程序")
            break

        elif user_input == "/a":
            token = login(fake_user_account.username, "secret")
            if token:
                print("重新登录成功！")
            else:
                print("重新登录失败，请检查用户名和密码")

        elif user_input == "/r":
            token = login("", "")
            if token:
                print("重新登录成功！")
            else:
                print("重新登录失败，请检查用户名和密码")
        elif user_input == "/g":
            if token:
                data = get_protected_data(token)
                if "error" in data and refresh_token_value:
                    print("访问失败，尝试刷新令牌...")
                    token = refresh_token(refresh_token_value)
                    if token:
                        data = get_protected_data(token)
                print("受保护数据响应:", data)
            else:
                print("请先登录")
        else:
            print("无效的操作，请重新输入")


if __name__ == "__main__":
    main()
