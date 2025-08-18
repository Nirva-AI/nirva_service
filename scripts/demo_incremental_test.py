#!/usr/bin/env python3
"""
增量分析器快速演示

这是一个简化版本的测试，展示增量分析的核心功能
"""

import requests
import time
import json
from datetime import datetime


# 配置
BASE_URL = "http://localhost:8000"
TEST_DATE = datetime.now().strftime("%Y-%m-%d")

# 简化的测试场景
DEMO_SCENARIOS = [
    {
        "name": "场景1: 咖啡店工作开始",
        "transcript": "早上9点我到了Blue Bottle Coffee，点了拿铁，准备开始工作。",
        "expected": "新事件",
        "reason": "这是第一个转录，应该创建新事件"
    },
    {
        "name": "场景2: 同事加入",
        "transcript": "Mark和Howard也到了咖啡店，我们开始讨论项目的技术方案。",
        "expected": "延续事件",
        "reason": "还在同一地点，相同活动类型，但参与人员增加"
    },
    {
        "name": "场景3: 会议继续",
        "transcript": "我们确定了下一阶段的开发计划，大家分工明确，会议很有效率。",
        "expected": "延续事件",
        "reason": "继续同一个工作会议"
    },
    {
        "name": "场景4: 离开咖啡店",
        "transcript": "会议结束了，我离开咖啡店，现在走在街上准备去超市。",
        "expected": "新事件",
        "reason": "地点变化了，从咖啡店到街上"
    },
    {
        "name": "场景5: 到达超市",
        "transcript": "到了超市，开始买今天需要的菜，想做意大利面。",
        "expected": "新事件",
        "reason": "地点和活动类型都改变了"
    }
]


def print_banner():
    """打印标题横幅"""
    print("🚀 " + "=" * 58 + " 🚀")
    print("                Nirva增量分析器演示                    ")
    print("🚀 " + "=" * 58 + " 🚀")
    print()


def send_transcript(transcript: str) -> dict:
    """发送转录内容"""
    try:
        # 注意：这里使用mock认证，实际使用时需要真实token
        response = requests.post(
            f"{BASE_URL}/action/analyze/incremental/v1/",
            json={
                "time_stamp": TEST_DATE,
                "new_transcript": transcript
            },
            headers={"Authorization": "Bearer mock_token"},
            timeout=30
        )
        
        if response.status_code == 200:
            return {"success": True, "data": response.json()}
        else:
            return {"success": False, "error": f"HTTP {response.status_code}: {response.text}"}
            
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_events() -> dict:
    """获取当前事件列表"""
    try:
        response = requests.post(
            f"{BASE_URL}/action/analyze/events/get/v1/",
            json={"time_stamp": TEST_DATE},
            headers={"Authorization": "Bearer mock_token"},
            timeout=15
        )
        
        if response.status_code == 200:
            return {"success": True, "data": response.json()}
        else:
            return {"success": False, "error": f"HTTP {response.status_code}: {response.text}"}
            
    except Exception as e:
        return {"success": False, "error": str(e)}


def display_events(events: list):
    """显示事件列表"""
    if not events:
        print("   📋 当前没有事件")
        return
    
    print(f"   📋 共 {len(events)} 个事件:")
    for i, event in enumerate(events, 1):
        people = ", ".join(event.get('people_involved', [])) if event.get('people_involved') else "独自"
        print(f"   {i}. {event.get('event_title', 'N/A')}")
        print(f"      📍 {event.get('location', 'N/A')} | 🏷️ {event.get('activity_type', 'N/A')}")
        print(f"      👥 {people}")
        print()


def run_demo():
    """运行演示"""
    print_banner()
    print(f"📅 测试日期: {TEST_DATE}")
    print(f"🌐 服务器: {BASE_URL}")
    print()
    
    # 检查服务器
    try:
        response = requests.get(f"{BASE_URL}/docs", timeout=5)
        if response.status_code != 200:
            print("❌ 服务器无法访问！请先启动:")
            print("   make run-appservice")
            print("   make run-analyzer")
            return
    except:
        print("❌ 服务器无法连接！请确保服务正在运行。")
        return
    
    print("✅ 服务器连接正常")
    print()
    
    # 运行测试场景
    for i, scenario in enumerate(DEMO_SCENARIOS, 1):
        print("🎬 " + "=" * 50)
        print(f"   {scenario['name']}")
        print("🎬 " + "=" * 50)
        
        print(f"📝 转录内容:")
        print(f"   {scenario['transcript']}")
        print()
        
        print(f"🎯 预期结果: {scenario['expected']}")
        print(f"💡 原因: {scenario['reason']}")
        print()
        
        print("⏳ 发送转录到服务器...")
        
        # 发送转录
        result = send_transcript(scenario['transcript'])
        
        if result['success']:
            data = result['data']
            print("✅ 处理成功!")
            print(f"   📊 新增事件: {data['new_events_count']}")
            print(f"   📊 更新事件: {data['updated_events_count']}")
            print(f"   📊 总事件数: {data['total_events_count']}")
            print(f"   💬 消息: {data['message']}")
            
            # 判断是否符合预期
            if scenario['expected'] == "新事件" and data['new_events_count'] > 0:
                print("   🎉 ✅ 符合预期：创建了新事件！")
            elif scenario['expected'] == "延续事件" and data['updated_events_count'] > 0:
                print("   🎉 ✅ 符合预期：更新了现有事件！")
            else:
                print("   ⚠️ 与预期不同，但可能有其他原因")
            
        else:
            print(f"❌ 处理失败: {result['error']}")
        
        print()
        
        # 获取当前事件状态
        print("📊 当前事件状态:")
        events_result = get_events()
        if events_result['success']:
            display_events(events_result['data']['events'])
        else:
            print(f"   ❌ 无法获取事件: {events_result['error']}")
        
        # 添加暂停，让用户能看清楚
        if i < len(DEMO_SCENARIOS):
            print("⏸️  按回车键继续下一个场景...")
            input()
            print()
    
    # 最终总结
    print("🏁 " + "=" * 50)
    print("             演示完成")
    print("🏁 " + "=" * 50)
    
    final_events = get_events()
    if final_events['success']:
        events_data = final_events['data']
        print(f"🎯 最终结果:")
        print(f"   📅 日期: {events_data['time_stamp']}")
        print(f"   📊 总事件数: {events_data['total_count']}")
        print(f"   🕒 最后更新: {events_data['last_updated']}")
        print()
        
        display_events(events_data['events'])
        
        # 保存结果
        filename = f"demo_results_{TEST_DATE}.json"
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(events_data, f, ensure_ascii=False, indent=2)
        print(f"💾 完整结果已保存到: {filename}")
        
    else:
        print(f"❌ 无法获取最终状态: {final_events['error']}")
    
    print()
    print("✨ 演示完成！")
    print("💡 提示:")
    print("   - 这展示了AI如何智能判断事件边界")
    print("   - 相同地点和活动会合并到一个事件")
    print("   - 地点或活动变化会创建新事件")
    print("   - 参与人员变化会更新事件信息")


if __name__ == "__main__":
    run_demo() 