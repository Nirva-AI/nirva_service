#!/usr/bin/env python3
"""
增量分析器测试脚本

测试新增的增量分析功能：
1. 增量转录处理
2. 事件获取
"""

import asyncio
import json
import requests
from datetime import datetime

# 配置
BASE_URL = "http://localhost:8000"
TEST_USERNAME = "test_user@example.com"
TEST_PASSWORD = "test_password"
TIME_STAMP = datetime.now().strftime("%Y-%m-%d")


def get_auth_token() -> str:
    """获取认证token（简化版，实际需要实现完整的认证流程）"""
    # 这里需要根据实际的认证系统来获取token
    # 暂时返回一个模拟的token
    return "mock_token"


def test_incremental_analyze():
    """测试增量分析功能"""
    
    print("=" * 60)
    print("测试增量分析功能")
    print("=" * 60)
    
    # 模拟第一次转录内容
    first_transcript = """
    今天早上9点到了Blue Bottle Coffee，准备开始工作。
    点了一杯拿铁，找了一个靠窗的位置坐下。
    """
    
    print(f"第一次转录: {first_transcript.strip()}")
    
    response1 = requests.post(
        f"{BASE_URL}/action/analyze/incremental/v1/",
        json={
            "time_stamp": TIME_STAMP,
            "new_transcript": first_transcript
        },
        headers={"Authorization": f"Bearer {get_auth_token()}"}
    )
    
    if response1.status_code == 200:
        result1 = response1.json()
        print(f"✅ 第一次分析成功:")
        print(f"   新增事件: {result1['new_events_count']}")
        print(f"   更新事件: {result1['updated_events_count']}")
        print(f"   总事件数: {result1['total_events_count']}")
        print(f"   消息: {result1['message']}")
    else:
        print(f"❌ 第一次分析失败: {response1.status_code} - {response1.text}")
        return
    
    print("\n" + "-" * 40)
    
    # 模拟第二次转录内容（延续第一个事件）
    second_transcript = """
    刚才Mark和Howard也到了咖啡店，我们开始讨论项目的进展。
    大家对新功能的开发计划达成了一致，氛围很好。
    """
    
    print(f"第二次转录（应该是延续）: {second_transcript.strip()}")
    
    response2 = requests.post(
        f"{BASE_URL}/action/analyze/incremental/v1/",
        json={
            "time_stamp": TIME_STAMP,
            "new_transcript": second_transcript
        },
        headers={"Authorization": f"Bearer {get_auth_token()}"}
    )
    
    if response2.status_code == 200:
        result2 = response2.json()
        print(f"✅ 第二次分析成功:")
        print(f"   新增事件: {result2['new_events_count']}")
        print(f"   更新事件: {result2['updated_events_count']}")
        print(f"   总事件数: {result2['total_events_count']}")
        print(f"   消息: {result2['message']}")
    else:
        print(f"❌ 第二次分析失败: {response2.status_code} - {response2.text}")
        return
    
    print("\n" + "-" * 40)
    
    # 模拟第三次转录内容（新事件）
    third_transcript = """
    会议结束了，我离开了咖啡店，现在在回家的路上。
    准备在超市买一些菜，晚上自己做饭。
    """
    
    print(f"第三次转录（应该是新事件）: {third_transcript.strip()}")
    
    response3 = requests.post(
        f"{BASE_URL}/action/analyze/incremental/v1/",
        json={
            "time_stamp": TIME_STAMP,
            "new_transcript": third_transcript
        },
        headers={"Authorization": f"Bearer {get_auth_token()}"}
    )
    
    if response3.status_code == 200:
        result3 = response3.json()
        print(f"✅ 第三次分析成功:")
        print(f"   新增事件: {result3['new_events_count']}")
        print(f"   更新事件: {result3['updated_events_count']}")
        print(f"   总事件数: {result3['total_events_count']}")
        print(f"   消息: {result3['message']}")
    else:
        print(f"❌ 第三次分析失败: {response3.status_code} - {response3.text}")


def test_get_events():
    """测试获取事件功能"""
    
    print("\n" + "=" * 60)
    print("测试获取事件功能")
    print("=" * 60)
    
    response = requests.post(
        f"{BASE_URL}/action/analyze/events/get/v1/",
        json={
            "time_stamp": TIME_STAMP
        },
        headers={"Authorization": f"Bearer {get_auth_token()}"}
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ 获取事件成功:")
        print(f"   时间戳: {result['time_stamp']}")
        print(f"   事件总数: {result['total_count']}")
        print(f"   最后更新: {result['last_updated']}")
        
        print(f"\n📋 事件详情:")
        for i, event in enumerate(result['events'], 1):
            print(f"   {i}. {event['event_title']}")
            print(f"      时间: {event['time_range']}")
            print(f"      地点: {event['location']}")
            print(f"      类型: {event['activity_type']}")
            print(f"      参与者: {', '.join(event['people_involved']) if event['people_involved'] else '独自'}")
            print(f"      摘要: {event['one_sentence_summary'][:100]}...")
            print()
    else:
        print(f"❌ 获取事件失败: {response.status_code} - {response.text}")


def test_api_availability():
    """测试API可用性"""
    
    print("=" * 60)
    print("测试API可用性")
    print("=" * 60)
    
    # 测试服务器是否运行
    try:
        response = requests.get(f"{BASE_URL}/docs", timeout=5)
        if response.status_code == 200:
            print("✅ 服务器运行正常")
        else:
            print(f"⚠️  服务器响应异常: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"❌ 无法连接到服务器: {e}")
        print("请确保服务器在 http://localhost:8000 运行")
        return False
    
    return True


def main():
    """主测试函数"""
    
    print("🚀 增量分析器功能测试")
    print(f"📅 测试时间戳: {TIME_STAMP}")
    print(f"🌐 服务器地址: {BASE_URL}")
    
    # 检查API可用性
    if not test_api_availability():
        return
    
    print("\n⚠️  注意: 这个测试脚本需要:")
    print("1. 服务器在 http://localhost:8000 运行")
    print("2. 正确的认证token（当前使用模拟token）")
    print("3. 数据库连接正常")
    print("\n继续测试...\n")
    
    # 测试增量分析
    test_incremental_analyze()
    
    # 测试获取事件
    test_get_events()
    
    print("\n" + "=" * 60)
    print("✨ 测试完成!")
    print("=" * 60)


if __name__ == "__main__":
    main() 