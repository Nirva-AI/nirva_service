import requests
from typing import Final, Optional, Dict, cast

# 服务器地址
BASE_URL: Final[str] = "http://localhost:8000"


def login() -> Optional[str]:
    username = input("请输入用户名: ")
    password = input("请输入密码: ")

    response = requests.post(
        f"{BASE_URL}/token",
        data={"username": username, "password": password, "grant_type": "password"},
    )

    if response.status_code == 200:
        token: str = response.json()["access_token"]
        print("登录成功！令牌已获取")
        return token
    else:
        print("登录失败，请检查用户名和密码")
        return None


def get_protected_data(token: str) -> Dict[str, str]:
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/protected-data", headers=headers)

    if response.status_code == 200:
        return cast(Dict[str, str], response.json())
    else:
        return {"error": "访问失败"}


def main() -> None:
    # 测试流程
    while True:

        user_input = input(
            "请输入操作: /q 是退出, /r 是重新登录: /g 是获取受保护数据: "
        )
        if user_input == "/q":
            print("退出程序")
            break
        elif user_input == "/r":
            token = login()
            if token:
                print("重新登录成功！")
            else:
                print("重新登录失败，请检查用户名和密码")
        elif user_input == "/g":
            if token:
                data = get_protected_data(token)
                print("受保护数据响应:", data)
            else:
                print("请先登录")
        else:
            print("无效的操作，请重新输入")


if __name__ == "__main__":
    main()
