import requests

# 服务器地址
BASE_URL = "http://localhost:8000"

def login():
    username = input("请输入用户名: ")
    password = input("请输入密码: ")
    
    response = requests.post(
        f"{BASE_URL}/token",
        data={"username": username, "password": password, "grant_type": "password"}
    )
    
    if response.status_code == 200:
        token = response.json()["access_token"]
        print("登录成功！令牌已获取")
        return token
    else:
        print("登录失败，请检查用户名和密码")
        return None

def get_protected_data(token: str):
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/protected-data", headers=headers)
    
    if response.status_code == 200:
        return response.json()
    else:
        return {"error": "访问失败"}

if __name__ == "__main__":
    # 测试流程
    token = login()
    if token:
        data = get_protected_data(token)
        print("受保护数据响应:", data)