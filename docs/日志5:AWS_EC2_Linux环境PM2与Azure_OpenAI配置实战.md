# 日志5: AWS EC2 Linux环境PM2与Azure OpenAI配置实战

**日期**: 2025年7月18日  
**环境**: AWS EC2 Linux (Amazon Linux 2023)  
**分支**: yh-aws-ec2-linux  
**目标**: 在EC2环境中配置PM2进程管理器和Azure OpenAI环境变量

---

## 1. 任务背景

### 1.1 项目同步状态确认
- **问题**: 需要确认nirva_service项目在EC2环境中的分支状态并与远程仓库同步
- **解决方案**: 
  - 确认当前分支为 `yh-aws-ec2-linux`
  - 执行 `git fetch origin` 和 `git pull origin yh-aws-ec2-linux`
  - 成功同步了1个提交，更新了6个文件

### 1.2 开发环境一致性需求
- **背景**: 用户在MacBook Pro上已经使用PM2管理Python应用，并通过GitHub同步到EC2
- **需求**: 在EC2 Linux环境中复现相同的开发环境配置

---

## 2. PM2进程管理器配置

### 2.1 PM2可行性分析
**结论**: ✅ 在EC2 Linux上完全可以使用PM2管理conda Python应用

**优势**:
- 进程管理: 自动重启、负载均衡、日志管理
- 多服务管理: 项目包含3个服务（chat、analyzer、appservice）
- 生产环境友好: 适合部署到生产环境
- 与conda兼容: PM2会使用当前激活的conda环境

### 2.2 安装过程
```bash
# 1. 添加NodeSource官方源
curl -fsSL https://rpm.nodesource.com/setup_20.x | sudo bash -

# 2. 安装Node.js
sudo dnf install nodejs -y

# 3. 全局安装PM2
sudo npm install -g pm2
```

### 2.3 安装结果
- **Node.js**: v20.19.4 (LTS)
- **npm**: 10.8.2
- **PM2**: 6.0.8
- **安装路径**: `/usr/bin/pm2`

### 2.4 项目中的PM2配置
项目中已包含PM2脚本：
```bash
# scripts/run_pm2script.sh
#!/bin/bash
pm2 delete all
./scripts/kill_ports.sh
pm2 start scripts/run_chat_server.py scripts/run_analyzer_server.py scripts/run_appservice_server.py
```

---

## 3. Azure OpenAI环境变量配置

### 3.1 问题描述
- **代码需求**: `chat_azure_openai_gpt_4o_graph.py`中需要读取环境变量
  ```python
  llm = AzureChatOpenAI(
      azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
      api_key=SecretStr(str(os.getenv("AZURE_OPENAI_API_KEY"))),
      azure_deployment="gpt-4o",
      api_version="2024-02-01",
      temperature=temperature,
  )
  ```
- **用户现状**: 在MacBook Pro的zsh中已配置，但不知道如何在Linux上配置

### 3.2 解决方案

#### 方案一: 配置到~/.bashrc (推荐)
```bash
# 添加环境变量到~/.bashrc
echo -e "\n# Azure OpenAI Configuration
export AZURE_OPENAI_ENDPOINT=https://bolin-east-us.openai.azure.com/
export AZURE_OPENAI_API_KEY=4170e4ef99184df2bd6dbfd97a2b57b1" >> ~/.bashrc

# 重新加载配置
source ~/.bashrc
```

#### 方案二: 创建.env文件 (项目级别)
```bash
# 在项目根目录创建.env文件
cat > .env << EOF
# Azure OpenAI Configuration
AZURE_OPENAI_ENDPOINT=https://bolin-east-us.openai.azure.com/
AZURE_OPENAI_API_KEY=4170e4ef99184df2bd6dbfd97a2b57b1
EOF

# 添加到.gitignore
echo ".env" >> .gitignore
```

### 3.3 配置验证
```bash
# 验证环境变量
echo "AZURE_OPENAI_ENDPOINT: $AZURE_OPENAI_ENDPOINT"
echo "AZURE_OPENAI_API_KEY: $AZURE_OPENAI_API_KEY"

# Python验证
python -c "import os; print('AZURE_OPENAI_ENDPOINT:', os.getenv('AZURE_OPENAI_ENDPOINT')); print('AZURE_OPENAI_API_KEY:', os.getenv('AZURE_OPENAI_API_KEY'))"
```

**结果**: ✅ 环境变量配置成功，Python代码能正确读取

---

## 4. 环境状态总结

### 4.1 当前conda环境
- **活跃环境**: `nirva`
- **Python版本**: 3.12.11
- **Python路径**: `/home/ec2-user/miniconda3/envs/nirva/bin/python`

### 4.2 工具链状态
- **✅ Conda**: 已配置并激活nirva环境
- **✅ Node.js**: v20.19.4 已安装
- **✅ PM2**: 6.0.8 已安装并可用
- **✅ Azure OpenAI**: 环境变量已配置

### 4.3 项目就绪状态
- **✅ Git同步**: 与远程仓库同步完成
- **✅ PM2脚本**: 项目中的PM2脚本可以直接使用
- **✅ 环境变量**: Azure OpenAI配置完成
- **✅ Python环境**: conda环境正常运行

---

## 5. 后续建议

### 5.1 立即可执行的操作
1. 使用 `./scripts/run_pm2script.sh` 启动服务
2. 使用 `make run-all` 通过Makefile启动服务
3. 测试Azure OpenAI功能

### 5.2 生产环境考虑
1. **安全性**: 
   - 考虑将API密钥放在更安全的地方
   - 使用AWS Secrets Manager或参数存储
2. **PM2配置**:
   - 配置PM2开机自启动: `pm2 startup`
   - 保存PM2配置: `pm2 save`
3. **监控**:
   - 使用 `pm2 monit` 监控进程状态
   - 配置日志轮转

### 5.3 开发环境优化
1. **IDE配置**: 确保VS Code Remote SSH使用正确的Python解释器
2. **调试配置**: 配置断点调试环境
3. **热重载**: 配置开发环境的自动重启

---

## 6. 关键命令参考

### 6.1 PM2常用命令
```bash
pm2 start app.py                # 启动应用
pm2 list                         # 查看所有进程
pm2 stop all                     # 停止所有进程
pm2 restart all                  # 重启所有进程
pm2 delete all                   # 删除所有进程
pm2 logs                         # 查看日志
pm2 monit                        # 监控界面
```

### 6.2 环境变量管理
```bash
# 查看环境变量
env | grep AZURE

# 临时设置环境变量
export AZURE_OPENAI_ENDPOINT=your_endpoint

# 重新加载bashrc
source ~/.bashrc
```

### 6.3 项目管理
```bash
# 激活conda环境
conda activate nirva

# 使用项目Makefile
make run-all                     # 启动所有服务
make help                        # 查看所有可用命令
```

---

## 7. 技术要点总结

### 7.1 跨平台环境同步
- **成功经验**: 通过Git同步代码 + 配置文件的方式实现跨平台开发
- **配置管理**: 使用环境变量和配置文件分离敏感信息
- **工具链一致性**: 在不同平台上使用相同的工具链（PM2、conda等）

### 7.2 Linux环境配置要点
- **Shell配置**: 使用~/.bashrc配置环境变量（类似macOS的~/.zshrc）
- **权限管理**: 使用sudo安装全局工具，注意用户权限
- **包管理**: 使用系统包管理器（dnf）+ npm的混合管理方式

### 7.3 Python+PM2最佳实践
- **环境隔离**: PM2会自动使用当前激活的conda环境
- **进程管理**: 使用PM2管理多个Python服务
- **日志管理**: 利用PM2的日志功能进行统一日志管理

---

**本次配置完成时间**: 2025年7月18日  
**状态**: ✅ 完成，环境已就绪，可以开始后续开发工作
