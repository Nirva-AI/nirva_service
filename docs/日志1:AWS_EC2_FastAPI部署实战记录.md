# 日志1：AWS EC2 FastAPI部署实战记录

**日期**: 2025年7月15日  
**目标**: 在AWS EC2上部署FastAPI应用，并通过本地客户端访问  
**状态**: ✅ 成功完成

## 📋 项目背景

作为AWS新手，希望通过实际操作学习：

1. AWS EC2实例的创建和管理
2. FastAPI应用的云端部署
3. 网络安全组配置
4. 本地客户端访问云端服务

## 🎯 学习目标

- [x] 理解AWS Load Balancer (ALB) 的作用和最佳实践
- [x] 掌握EC2实例的创建和配置
- [x] 学会安全组的配置方法
- [x] 成功部署并运行FastAPI应用
- [x] 实现本地到云端的API调用

## 🛠️ 技术架构

```text
Internet → AWS ALB → EC2实例(Amazon Linux 2023) → FastAPI(8000端口)
                                                  ↑
                                            SSH连接(22端口)
```

## 📖 知识点学习

### 1. AWS Load Balancer

- **ALB (Application Load Balancer)**: 应用层负载均衡器，工作在第7层
- **本质**: 类似"Nginx即服务"，但完全托管，无需维护
- **优势**: 自动扩缩容、高可用性保证、深度AWS集成

### 2. EC2 (Elastic Compute Cloud)

- **本质**: 虚拟化的计算实例，云端虚拟机
- **特点**: 弹性、按需付费、完全控制
- **类比**: 类似本地VMware虚拟机，但运行在AWS数据中心

### 3. .pem密钥文件

- **作用**: SSH连接的"钥匙"，替代用户名+密码
- **安全性**: 比密码更安全，包含私钥信息
- **重要性**: 丢失无法连接实例，需妥善保管

## 🚀 实施步骤详解

### 第一步：创建EC2实例

#### 基础配置

```yaml
实例名称: my-fastapi-server
AMI: Amazon Linux 2023 AMI (免费层)
实例类型: t2.micro (免费层)
密钥对: my-ec2-key (新创建)
```

#### 网络安全组配置

```yaml
安全组名称: launch-wizard-1
入站规则:
  - SSH: TCP, 22, 0.0.0.0/0
  - 自定义TCP: TCP, 8000, 0.0.0.0/0
出站规则: 全部允许
```

#### ⚠️ 问题与解决

**问题**: 初始连接失败  
**原因**: 安全组缺少SSH(22端口)规则  
**解决**: 手动添加SSH入站规则  

### 第二步：环境准备

#### 系统更新

```bash
sudo yum update -y
# 结果: Dependencies resolved. Nothing to do. Complete!
```

#### Python环境安装

```bash
sudo yum install python3 python3-pip -y
# 结果: python3-3.9.23 已安装, pip安装成功
```

#### FastAPI依赖安装

```bash
pip3 install fastapi uvicorn
# 成功安装: fastapi-0.116.1, uvicorn-0.35.0
```

### 第三步：FastAPI应用开发

#### 应用代码 (app.py)

```python
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "Hello World from EC2!", "status": "success"}

@app.get("/health")
def health_check():
    return {"status": "healthy", "server": "AWS EC2"}

@app.get("/items/{item_id}")
def read_item(item_id: int, q: str = None):
    return {"item_id": item_id, "q": q, "server": "EC2"}
```

#### 文件操作

```bash
# 创建应用文件
nano app.py

# 验证文件内容
cat app.py
ls -la
```

### 第四步：应用部署

#### 启动命令

```bash
uvicorn app:app --host 0.0.0.0 --port 8000
```

#### 启动结果

```bash
Started server process [9772]
Waiting for application startup.
Application startup complete.
Uvicorn running on http://0.0.0.0:8000
```

## 🌐 访问测试

### 实例信息

- **实例ID**: i-05c680f1c2dd794c7
- **公网IP**: 44.203.54.30
- **内网IP**: 172.31.88.55

### API端点测试

```bash
# 主页
curl http://44.203.54.30:8000/
# 响应: {"message": "Hello World from EC2!", "status": "success"}

# 健康检查
curl http://44.203.54.30:8000/health
# 响应: {"status": "healthy", "server": "AWS EC2"}

# API文档
浏览器访问: http://44.203.54.30:8000/docs
```

## 💡 最佳实践总结

### 安全配置

1. **最小权限原则**: 生产环境应限制源IP访问
2. **密钥管理**: .pem文件需要安全存储
3. **端口管理**: 只开放必要的端口

### 部署优化

1. **进程管理**: 生产环境建议使用systemd或supervisor
2. **反向代理**: 可考虑nginx + uvicorn组合
3. **监控日志**: 配置CloudWatch监控

### 成本控制

1. **实例管理**: 不使用时及时停止实例
2. **资源监控**: 关注免费层使用情况
3. **自动关机**: 设置定时任务避免忘记关机

## 🎓 学习收获

### 技术技能

- [x] 掌握AWS EC2实例的完整创建流程
- [x] 理解云安全组的配置原理
- [x] 学会在Linux服务器上部署Python应用
- [x] 熟悉基本的Linux命令操作

### 云计算理念

- [x] 理解IaaS层服务的特点
- [x] 体验云资源的弹性和便利性
- [x] 认识到云安全配置的重要性

### 问题解决能力

- [x] 学会通过日志排查连接问题
- [x] 掌握安全组规则的调试方法
- [x] 提升了独立解决技术问题的能力

## 📚 扩展学习方向

### 后续可以探索的内容

1. **负载均衡**: 配置ALB进行流量分发
2. **数据库集成**: 连接RDS数据库服务
3. **容器化部署**: 使用Docker + ECS
4. **CI/CD管道**: GitHub Actions + AWS CodeDeploy
5. **监控告警**: CloudWatch + SNS通知

### 生产环境改进

1. **HTTPS配置**: 使用Certificate Manager
2. **域名绑定**: Route 53 DNS管理
3. **备份策略**: EBS快照和S3存储
4. **高可用架构**: 多AZ部署

## 🏆 项目总结

这次AWS EC2 + FastAPI部署实战是一次非常成功的云计算学习体验。从零开始，我们完整地体验了：

1. **云资源创建**: EC2实例的规划和配置
2. **网络安全**: 安全组规则的设计和调试
3. **应用部署**: 从代码编写到服务启动的完整流程
4. **问题解决**: 遇到连接问题时的系统性排查方法

通过这个项目，不仅掌握了AWS的基础操作，更重要的是建立了云计算的思维模式，为后续更复杂的云架构学习打下了坚实的基础。

---

**下次改进目标**: 尝试使用Docker容器化部署，并配置ALB实现负载均衡。
