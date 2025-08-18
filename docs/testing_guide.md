# 🧪 增量分析器测试指南

## 📋 测试概述

我们为增量分析器创建了两个测试脚本，帮助你验证所有功能是否符合预期：

1. **🎬 快速演示** (`demo_incremental_test.py`) - 交互式演示，展示核心功能
2. **🔬 综合测试** (`comprehensive_test_incremental.py`) - 完整的自动化测试

## 🚀 开始测试

### 前置条件

1. **启动所有服务**：
```bash
# 激活环境
conda activate nirva

# 启动AppService (包含增量分析API)
make run-appservice

# 在新终端启动Analyzer服务
make run-analyzer
```

2. **验证服务运行**：
   - AppService: http://localhost:8000/docs
   - Analyzer: http://localhost:8200/docs

### 🎬 快速演示 (推荐新手)

这个演示脚本会一步步展示增量分析的工作流程：

```bash
python scripts/demo_incremental_test.py
```

**演示场景**：
- 场景1: 到咖啡店开始工作 → 创建新事件
- 场景2: 同事加入会议 → 更新现有事件
- 场景3: 会议继续 → 继续更新
- 场景4: 离开咖啡店 → 创建新事件
- 场景5: 到达超市 → 创建新事件

**特点**：
- 📱 交互式：每个场景后按回车继续
- 🎯 有预期：每步都说明预期结果
- 👀 可视化：清晰显示事件变化

### 🔬 综合测试 (完整验证)

这个测试脚本模拟一整天的转录时间线：

```bash
python scripts/comprehensive_test_incremental.py
```

**测试特点**：
- ⏰ 14个时间点的转录内容
- 🤖 自动化运行，无需人工干预
- 📊 详细的准确率分析
- 🧪 包含边缘情况测试
- 💾 自动保存测试结果

## 📊 测试结果解读

### 成功指标

1. **事件创建准确性**：
   - 地点变化 → 应该创建新事件
   - 活动类型变化 → 应该创建新事件
   - 相同环境延续 → 应该更新现有事件

2. **AI判断准确率**：
   - 目标：>80% 准确率
   - 新事件预测正确
   - 事件延续预测正确

3. **数据完整性**：
   - 事件信息完整（标题、地点、类型、参与者）
   - 时间戳正确
   - 内容合并正确

### 示例输出

```
🎯 预期行为分析:
   09:00: ✅ 正确预测新事件
   09:05: ✅ 正确预测事件延续
   09:10: ✅ 正确预测事件延续
   10:45: ✅ 正确预测新事件
   11:00: ✅ 正确预测新事件

🎯 AI判断准确率: 85.7% (12/14)
```

## 🔧 问题排查

### 常见错误

#### 1. 服务器连接失败
```
❌ 服务器无法连接！请确保服务正在运行。
```

**解决方案**：
```bash
# 检查服务状态
curl http://localhost:8000/docs
curl http://localhost:8200/docs

# 重新启动服务
make run-appservice
make run-analyzer
```

#### 2. 认证失败
```
HTTP 401: Unauthorized
```

**解决方案**：
- 测试脚本使用mock token，如果你的系统需要真实认证，请在脚本中更新 `AUTH_TOKEN`

#### 3. AI分析超时
```
处理失败: Timeout
```

**解决方案**：
- 检查Analyzer服务是否正常
- 检查OpenAI API key是否配置
- 增加timeout时间

#### 4. 数据库错误
```
保存事件失败: database connection error
```

**解决方案**：
```bash
# 检查数据库状态
psql -h localhost -U your_user -d your_db

# 重新初始化数据库
python scripts/run_dev_clear_db.py
```

### 调试技巧

1. **查看详细日志**：
   - AppService日志：查看增量分析处理过程
   - Analyzer日志：查看AI分析结果

2. **手动测试单个接口**：
```bash
# 测试增量分析
curl -X POST http://localhost:8000/action/analyze/incremental/v1/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer mock_token" \
  -d '{
    "time_stamp": "2025-01-18",
    "new_transcript": "测试转录内容"
  }'

# 测试事件查询
curl -X POST http://localhost:8000/action/analyze/events/get/v1/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer mock_token" \
  -d '{"time_stamp": "2025-01-18"}'
```

3. **检查生成的文件**：
   - `test_results_YYYY-MM-DD.json` - 完整测试结果
   - `demo_results_YYYY-MM-DD.json` - 演示结果

## 📈 自定义测试

### 添加新的测试场景

你可以在测试脚本中添加自己的场景：

```python
# 在 DEMO_SCENARIOS 或 TRANSCRIPT_TIMELINE 中添加
{
    "name": "自定义场景",
    "transcript": "你的转录内容",
    "expected": "新事件" 或 "延续事件",
    "reason": "解释为什么这样预期"
}
```

### 测试特定用例

创建针对特定场景的测试：

```python
def test_your_scenario():
    # 发送你的转录内容
    result = send_transcript("你的转录内容")
    
    # 验证结果
    assert result['success']
    assert result['data']['new_events_count'] == 1  # 或你的预期
    
    # 获取事件
    events = get_events()
    assert len(events['data']['events']) == 预期数量
```

## 🎯 性能基准

### 预期响应时间

- **增量分析**: < 10秒 (包含AI处理)
- **事件查询**: < 1秒
- **数据库操作**: < 100ms

### 吞吐量

- **并发用户**: 建议 < 10 (AI处理限制)
- **转录频率**: 每3-5分钟一次
- **单次转录长度**: < 1000字符

## ✅ 验收标准

测试通过需要满足：

1. **功能正确性**: 所有API调用成功
2. **AI准确性**: 判断准确率 > 80%
3. **数据一致性**: 事件信息完整准确
4. **性能要求**: 响应时间在可接受范围
5. **错误处理**: 边缘情况处理正确

---

## 🆘 获取帮助

如果测试过程中遇到问题：

1. 检查所有服务是否正常运行
2. 查看日志文件中的错误信息
3. 验证数据库连接和API配置
4. 尝试重启服务并重新运行测试

测试成功后，你就可以确信增量分析器功能完全符合预期！🎉 