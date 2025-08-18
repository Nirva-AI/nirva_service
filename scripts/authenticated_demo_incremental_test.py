import sys
from pathlib import Path
import requests
import json
import asyncio
from typing import Dict, Any

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# 配置信息
BASE_URL = "http://localhost:8000"
TEST_USERNAME = "test_user@example.com"
TEST_PASSWORD = "test_password123"
TIME_STAMP = "2025-08-17"

def create_test_user() -> bool:
    """创建测试用户"""
    from nirva_service.db.pgsql_user import save_user, has_user
    from passlib.context import CryptContext
    
    # 检查用户是否已存在
    if has_user(TEST_USERNAME):
        print(f"✅ 测试用户 {TEST_USERNAME} 已存在")
        return True
    
    # 创建密码hash
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    hashed_password = pwd_context.hash(TEST_PASSWORD)
    
    # 创建用户
    user = save_user(
        username=TEST_USERNAME,
        hashed_password=hashed_password,
        display_name="Test User"
    )
    
    if user:
        print(f"✅ 测试用户创建成功: {TEST_USERNAME}")
        return True
    else:
        print(f"❌ 测试用户创建失败")
        return False

def get_auth_token() -> str:
    """获取认证token"""
    login_url = f"{BASE_URL}/login/v1/"
    
    # 准备登录数据
    login_data = {
        "username": TEST_USERNAME,
        "password": TEST_PASSWORD
    }
    
    try:
        response = requests.post(
            login_url,
            data=login_data,  # OAuth2PasswordRequestForm expects form data
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        if response.status_code == 200:
            token_data = response.json()
            access_token = token_data["access_token"]
            print(f"✅ 登录成功，获取到token")
            return access_token
        else:
            print(f"❌ 登录失败: {response.status_code} - {response.text}")
            return ""
    except Exception as e:
        print(f"❌ 登录请求失败: {e}")
        return ""

def test_incremental_analysis_with_auth(token: str):
    """使用认证token测试增量分析"""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # 测试场景
    scenarios = [
        {
            "transcript": "早上9点我到了Blue Bottle Coffee，点了拿铁，准备开始工作。",
            "description": "咖啡店工作开始",
            "expected": "新事件"
        },
        {
            "transcript": "Mark和Howard也到了咖啡店，我们开始讨论项目的技术方案。",
            "description": "同事加入",
            "expected": "延续事件"
        },
        {
            "transcript": "我们确定了下一阶段的开发计划，大家分工明确，会议很有效率。",
            "description": "会议继续",
            "expected": "延续事件"
        },
        {
            "transcript": "会议结束了，我离开咖啡店，现在走在街上准备去超市。",
            "description": "离开咖啡店",
            "expected": "新事件"
        },
        {
            "transcript": "到了超市，开始买今天需要的菜，想做意大利面。",
            "description": "到达超市",
            "expected": "新事件"
        }
    ]
    
    print("🚀 ========================================================== 🚀")
    print("                Nirva增量分析器认证测试                    ")
    print("🚀 ========================================================== 🚀")
    print(f"📅 测试日期: {TIME_STAMP}")
    print(f"👤 测试用户: {TEST_USERNAME}")
    print()
    
    for i, scenario in enumerate(scenarios, 1):
        print(f"🎬 ==================================================")
        print(f"   场景{i}: {scenario['description']}")
        print(f"🎬 ==================================================")
        print(f"📝 转录内容:\n   {scenario['transcript']}")
        print(f"🎯 预期结果: {scenario['expected']}")
        print()
        
        # 发送增量分析请求
        analyze_url = f"{BASE_URL}/action/analyze/incremental/v1/"
        analyze_data = {
            "time_stamp": TIME_STAMP,
            "new_transcript": scenario['transcript']
        }
        
        try:
            print("⏳ 发送转录到服务器...")
            response = requests.post(analyze_url, headers=headers, json=analyze_data)
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ 处理成功!")
                print(f"   📊 更新的事件数量: {result['updated_events_count']}")
                print(f"   🆕 新增的事件数量: {result['new_events_count']}")
                print(f"   📈 总事件数量: {result['total_events_count']}")
                print(f"   💬 消息: {result['message']}")
            else:
                print(f"❌ 处理失败: HTTP {response.status_code}")
                print(f"   详细错误: {response.text}")
                
        except Exception as e:
            print(f"❌ 请求失败: {e}")
        
        # 获取当前事件状态
        events_url = f"{BASE_URL}/action/analyze/events/get/v1/"
        events_data = {"time_stamp": TIME_STAMP}
        
        try:
            print("\n📊 当前事件状态:")
            response = requests.post(events_url, headers=headers, json=events_data)
            
            if response.status_code == 200:
                events_result = response.json()
                print(f"   📅 日期: {events_result['time_stamp']}")
                print(f"   📊 事件总数: {events_result['total_count']}")
                print(f"   🕒 最后更新: {events_result['last_updated']}")
                
                if events_result['events']:
                    print("   📋 事件列表:")
                    for j, event in enumerate(events_result['events'], 1):
                        print(f"     {j}. 📍 {event.get('location', 'N/A')} | "
                              f"👥 {', '.join(event.get('people', []))} | "
                              f"🎯 {event.get('activity_type', 'N/A')}")
                        print(f"        📝 {event.get('summary', 'N/A')[:100]}...")
                        
            else:
                print(f"   ❌ 无法获取事件: HTTP {response.status_code}")
                print(f"   详细错误: {response.text}")
                
        except Exception as e:
            print(f"   ❌ 请求失败: {e}")
        
        if i < len(scenarios):
            input("⏸️  按回车键继续下一个场景...\n")
        else:
            print("\n🏁 ==================================================")
            print("             认证测试完成")
            print("🏁 ==================================================")

def main():
    """主函数"""
    print("🚀 Nirva增量分析器认证测试")
    print("=" * 50)
    
    # 1. 创建测试用户
    print("1️⃣ 创建测试用户...")
    if not create_test_user():
        print("❌ 无法创建测试用户，退出测试")
        return
    
    # 2. 获取认证token
    print("\n2️⃣ 获取认证token...")
    token = get_auth_token()
    if not token:
        print("❌ 无法获取认证token，退出测试")
        return
    
    # 3. 运行增量分析测试
    print("\n3️⃣ 开始增量分析测试...")
    test_incremental_analysis_with_auth(token)
    
    print("\n✨ 测试完成！")
    print("💡 提示:")
    print("   - 这展示了AI如何智能判断事件边界")
    print("   - 相同地点和活动会合并到一个事件")
    print("   - 地点或活动变化会创建新事件")
    print("   - 参与人员变化会更新事件信息")

if __name__ == "__main__":
    main() 