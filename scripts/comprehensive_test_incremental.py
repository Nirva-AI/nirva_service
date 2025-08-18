#!/usr/bin/env python3
"""
增量分析器综合测试用例

模拟一整天的转录内容，测试：
1. 事件的智能新增和合并
2. 实时事件查询
3. AI判断逻辑的准确性
"""

import requests
import time
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any
import sys


# 配置
BASE_URL = "http://localhost:8000"
AUTH_TOKEN = "mock_token"  # 需要替换为真实token
TEST_DATE = datetime.now().strftime("%Y-%m-%d")

# 模拟的转录时间线（模拟一天的活动）
TRANSCRIPT_TIMELINE = [
    {
        "time": "09:00",
        "transcript": "今天早上9点，我到了市中心的Blue Bottle Coffee。天气很不错，我点了一杯拿铁，找了一个靠窗的座位。",
        "expected_action": "NEW",  # 预期是新事件
        "description": "第一个转录 - 应该创建新事件"
    },
    {
        "time": "09:05", 
        "transcript": "刚才服务员很友好，咖啡的味道也不错。我打开笔记本，准备开始今天的工作。周围有一些其他的客人，氛围很安静。",
        "expected_action": "CONTINUE",  # 预期是延续
        "description": "5分钟后 - 应该延续咖啡店事件"
    },
    {
        "time": "09:10",
        "transcript": "我开始查看今天的工作计划。有几个重要的任务需要完成，包括完成项目报告和准备下午的会议材料。",
        "expected_action": "CONTINUE", 
        "description": "10分钟后 - 继续在咖啡店工作"
    },
    {
        "time": "09:15",
        "transcript": "Mark刚才给我发消息说他和Howard也要过来。我们约定在这里讨论项目的下一步计划。",
        "expected_action": "CONTINUE",
        "description": "15分钟后 - 还是同一个工作事件，但参与人员要变化"
    },
    {
        "time": "09:25",
        "transcript": "Mark和Howard到了！我们开始讨论项目进展。Mark提到了一些技术难点，Howard分享了他的解决方案。大家的想法都很不错。",
        "expected_action": "CONTINUE", 
        "description": "25分钟后 - 团队会议开始，应该更新参与人员"
    },
    {
        "time": "09:35",
        "transcript": "我们对新功能的开发计划达成了一致。接下来三周的工作安排也确定了。会议很有效率，大家都很投入。",
        "expected_action": "CONTINUE",
        "description": "35分钟后 - 会议继续进行"
    },
    {
        "time": "10:30",
        "transcript": "会议结束了，我们在咖啡店聊了聊别的话题。Mark和Howard准备去另一个地方吃午餐，我也准备离开了。",
        "expected_action": "CONTINUE",
        "description": "1.5小时后 - 会议结束，但还在同一地点"
    },
    {
        "time": "10:45",
        "transcript": "我离开了咖啡店，现在在街上走路。准备去附近的超市买一些菜，晚上想自己做饭。",
        "expected_action": "NEW",  # 地点变化，新事件
        "description": "45分钟后 - 离开咖啡店，应该是新事件"
    },
    {
        "time": "10:50",
        "transcript": "街上的人流量还挺大的，有很多上班族。我走过了几个商店，看到有一些有趣的新店开业了。",
        "expected_action": "CONTINUE",
        "description": "50分钟后 - 继续在街上行走"
    },
    {
        "time": "11:00",
        "transcript": "到了超市，开始购买今天需要的食材。我想做意大利面，所以买了番茄酱、意面和一些蔬菜。",
        "expected_action": "NEW",  # 地点和活动都变化了
        "description": "11点 - 到达超市，应该是新事件"
    },
    {
        "time": "11:10",
        "transcript": "在超市遇到了邻居张阿姨，我们聊了聊最近的天气和社区的一些变化。她推荐了一些不错的蔬菜。",
        "expected_action": "CONTINUE",
        "description": "10分钟后 - 继续在超市，但有社交互动"
    },
    {
        "time": "11:25",
        "transcript": "购物完成了，我从超市出来，准备回家。今天买的东西不多，一个购物袋就够了。",
        "expected_action": "CONTINUE",
        "description": "25分钟后 - 购物结束，准备离开"
    },
    {
        "time": "11:35",
        "transcript": "我在回家的路上，经过了公园。看到有人在跑步和遛狗，天气真的很好。",
        "expected_action": "NEW", # 又是移动/通勤
        "description": "35分钟后 - 回家路上，新的移动事件"
    },
    {
        "time": "12:00",
        "transcript": "到家了！我把菜放进冰箱，准备先休息一下，然后开始准备午餐。家里很安静，很舒服。",
        "expected_action": "NEW",  # 到家了，新环境
        "description": "12点 - 到家，应该是新的居家事件"
    }
]


def print_section(title: str, char: str = "="):
    """打印分节标题"""
    print(f"\n{char * 60}")
    print(f" {title}")
    print(f"{char * 60}")


def print_subsection(title: str):
    """打印子标题"""
    print(f"\n{'-' * 40}")
    print(f" {title}")
    print(f"{'-' * 40}")


def check_server_availability() -> bool:
    """检查服务器是否可用"""
    try:
        response = requests.get(f"{BASE_URL}/docs", timeout=5)
        return response.status_code == 200
    except:
        return False


def send_incremental_transcript(transcript: str, expected_time: str) -> Dict[str, Any]:
    """发送增量转录内容"""
    try:
        response = requests.post(
            f"{BASE_URL}/action/analyze/incremental/v1/",
            json={
                "time_stamp": TEST_DATE,
                "new_transcript": transcript
            },
            headers={"Authorization": f"Bearer {AUTH_TOKEN}"},
            timeout=30
        )
        
        if response.status_code == 200:
            return {"success": True, "data": response.json()}
        else:
            return {"success": False, "error": f"HTTP {response.status_code}: {response.text}"}
            
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_current_events() -> Dict[str, Any]:
    """获取当前所有事件"""
    try:
        response = requests.post(
            f"{BASE_URL}/action/analyze/events/get/v1/",
            json={"time_stamp": TEST_DATE},
            headers={"Authorization": f"Bearer {AUTH_TOKEN}"},
            timeout=15
        )
        
        if response.status_code == 200:
            return {"success": True, "data": response.json()}
        else:
            return {"success": False, "error": f"HTTP {response.status_code}: {response.text}"}
            
    except Exception as e:
        return {"success": False, "error": str(e)}


def analyze_events(events: List[Dict]) -> None:
    """分析事件列表"""
    if not events:
        print("   📋 当前没有事件")
        return
    
    print(f"   📋 当前事件总数: {len(events)}")
    print()
    
    for i, event in enumerate(events, 1):
        people = ", ".join(event.get('people_involved', [])) if event.get('people_involved') else "独自"
        print(f"   {i}. 🎯 {event.get('event_title', 'N/A')}")
        print(f"      ⏰ 时间: {event.get('time_range', 'N/A')}")
        print(f"      📍 地点: {event.get('location', 'N/A')}")
        print(f"      🏷️  类型: {event.get('activity_type', 'N/A')}")
        print(f"      👥 参与者: {people}")
        print(f"      📝 摘要: {event.get('one_sentence_summary', 'N/A')[:80]}...")
        print()


def run_timeline_test():
    """运行时间线测试"""
    
    print_section("🚀 开始增量分析时间线测试")
    print(f"📅 测试日期: {TEST_DATE}")
    print(f"🌐 服务器: {BASE_URL}")
    print(f"📊 转录条目: {len(TRANSCRIPT_TIMELINE)} 条")
    
    results = []
    
    for i, item in enumerate(TRANSCRIPT_TIMELINE):
        print_subsection(f"{item['time']} - {item['description']}")
        
        print(f"📝 转录内容:")
        print(f"   {item['transcript']}")
        print(f"\n🎯 预期行为: {item['expected_action']}")
        
        # 发送转录内容
        result = send_incremental_transcript(item['transcript'], item['time'])
        
        if result['success']:
            data = result['data']
            print(f"\n✅ 处理成功:")
            print(f"   新增事件: {data['new_events_count']}")
            print(f"   更新事件: {data['updated_events_count']}")
            print(f"   总事件数: {data['total_events_count']}")
            print(f"   消息: {data['message']}")
            
            # 验证预期行为
            if item['expected_action'] == 'NEW' and data['new_events_count'] > 0:
                print(f"   🎉 符合预期: 创建了新事件")
            elif item['expected_action'] == 'CONTINUE' and data['updated_events_count'] > 0:
                print(f"   🎉 符合预期: 更新了现有事件")
            else:
                print(f"   ⚠️  行为异常: 预期{item['expected_action']}，但新增{data['new_events_count']}，更新{data['updated_events_count']}")
            
            # 记录结果
            results.append({
                'time': item['time'],
                'expected': item['expected_action'],
                'actual_new': data['new_events_count'],
                'actual_updated': data['updated_events_count'],
                'total': data['total_events_count'],
                'success': True
            })
            
        else:
            print(f"\n❌ 处理失败: {result['error']}")
            results.append({
                'time': item['time'],
                'expected': item['expected_action'],
                'success': False,
                'error': result['error']
            })
        
        # 获取当前事件状态
        events_result = get_current_events()
        if events_result['success']:
            events_data = events_result['data']
            print(f"\n📊 当前事件状态:")
            analyze_events(events_data['events'])
        else:
            print(f"\n❌ 获取事件失败: {events_result['error']}")
        
        # 添加延迟，模拟真实时间间隔
        if i < len(TRANSCRIPT_TIMELINE) - 1:
            print(f"\n⏳ 等待3秒（模拟时间间隔）...")
            time.sleep(3)
    
    return results


def print_summary(results: List[Dict]):
    """打印测试总结"""
    print_section("📊 测试结果总结")
    
    successful = [r for r in results if r.get('success', False)]
    failed = [r for r in results if not r.get('success', False)]
    
    print(f"✅ 成功处理: {len(successful)}/{len(results)} 条转录")
    print(f"❌ 处理失败: {len(failed)} 条转录")
    
    if failed:
        print(f"\n❌ 失败的转录:")
        for fail in failed:
            print(f"   {fail['time']}: {fail.get('error', 'Unknown error')}")
    
    if successful:
        print(f"\n📈 事件变化趋势:")
        for result in successful:
            action_type = "🆕" if result['actual_new'] > 0 else "🔄"
            print(f"   {result['time']}: {action_type} 总事件数: {result['total']} (新增: {result['actual_new']}, 更新: {result['actual_updated']})")
        
        # 分析预期vs实际
        print(f"\n🎯 预期行为分析:")
        correct_predictions = 0
        for result in successful:
            expected = result['expected']
            if expected == 'NEW' and result['actual_new'] > 0:
                correct_predictions += 1
                print(f"   {result['time']}: ✅ 正确预测新事件")
            elif expected == 'CONTINUE' and result['actual_updated'] > 0:
                correct_predictions += 1
                print(f"   {result['time']}: ✅ 正确预测事件延续")
            else:
                print(f"   {result['time']}: ❌ 预测不准确 (预期: {expected})")
        
        accuracy = (correct_predictions / len(successful)) * 100
        print(f"\n🎯 AI判断准确率: {accuracy:.1f}% ({correct_predictions}/{len(successful)})")


def test_edge_cases():
    """测试边缘情况"""
    print_section("🧪 边缘情况测试")
    
    edge_cases = [
        {
            "name": "空转录内容",
            "transcript": "",
            "expect_error": True
        },
        {
            "name": "很长的转录内容",
            "transcript": "这是一个很长的转录内容。" * 100,
            "expect_error": False
        },
        {
            "name": "特殊字符",
            "transcript": "今天我去了café，点了一杯latté ☕️ 😊",
            "expect_error": False
        }
    ]
    
    for case in edge_cases:
        print_subsection(f"测试: {case['name']}")
        result = send_incremental_transcript(case['transcript'], "test")
        
        if case['expect_error']:
            if not result['success']:
                print("✅ 按预期处理了错误情况")
            else:
                print("⚠️ 应该报错但没有报错")
        else:
            if result['success']:
                print("✅ 成功处理特殊情况")
            else:
                print(f"❌ 处理失败: {result['error']}")


def main():
    """主测试函数"""
    
    print("🧪 Nirva增量分析器综合测试")
    print("=" * 60)
    
    # 检查服务器可用性
    if not check_server_availability():
        print("❌ 服务器不可用!")
        print("请确保以下服务正在运行:")
        print("1. make run-appservice (端口8000)")
        print("2. make run-analyzer (端口8200)")
        sys.exit(1)
    
    print("✅ 服务器连接正常")
    
    # 运行主要测试
    results = run_timeline_test()
    
    # 打印总结
    print_summary(results)
    
    # 测试边缘情况
    test_edge_cases()
    
    # 最终事件状态
    print_section("🏁 最终事件状态")
    final_events = get_current_events()
    if final_events['success']:
        events_data = final_events['data']
        print(f"📅 日期: {events_data['time_stamp']}")
        print(f"🕒 最后更新: {events_data['last_updated']}")
        analyze_events(events_data['events'])
        
        # 导出结果
        with open(f"test_results_{TEST_DATE}.json", "w", encoding="utf-8") as f:
            json.dump(events_data, f, ensure_ascii=False, indent=2)
        print(f"\n💾 完整结果已保存到: test_results_{TEST_DATE}.json")
        
    else:
        print(f"❌ 无法获取最终状态: {final_events['error']}")
    
    print_section("✨ 测试完成!")
    print("如果发现问题，请检查:")
    print("1. 认证token是否正确")
    print("2. 所有服务是否正常运行") 
    print("3. 数据库连接是否正常")
    print("4. AI分析服务是否响应")


if __name__ == "__main__":
    main() 