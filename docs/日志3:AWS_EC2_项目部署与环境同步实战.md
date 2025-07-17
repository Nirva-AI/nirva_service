# 日志3：AWS EC2 项目部署与环境同步实战

**日期**: 2025年7月17日  
**目标**: 在AWS EC2上部署nirva_service项目，解决跨平台环境兼容性问题  
**状态**: ✅ 成功完成

## 📋 项目背景

基于之前的AWS EC2基础部署经验，本次目标是将完整的FastAPI项目（nirva_service）部署到生产环境，并选择AWS托管服务作为数据库和缓存解决方案。

## 🎯 核心目标

- [x] 将Python项目从本地迁移到AWS EC2
- [x] 解决macOS到Linux的跨平台兼容性问题
- [x] 选择AWS托管服务（RDS + ElastiCache）
- [x] 修复并同步环境配置文件
- [x] 建立稳定的Git工作流

## 🛠️ 技术架构选型

### 基础设施选择

```text
AWS EC2 t3.medium → AWS RDS PostgreSQL
                 → AWS ElastiCache Redis
                 → FastAPI Application
```

**决策对比**：
- ❌ **选项A：自建数据库** - 维护成本高，需要手动备份和监控
- ✅ **选项B：AWS托管服务** - 自动备份、监控、扩缩容，更适合生产环境

### 环境架构

```text
开发环境(macOS ARM64) → 生产环境(Linux x86_64)
        ↓
Miniconda + Conda环境管理
        ↓
nirva_service FastAPI项目
```

## 🚀 部署流程详解

### 第一步：服务器环境准备

#### 系统信息确认
```bash
# 系统版本
Amazon Linux 2023.8 x86_64

# 架构确认
uname -m  # x86_64
```

#### Miniconda安装
```bash
# 下载并安装Miniconda
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
bash Miniconda3-latest-Linux-x86_64.sh

# 验证安装
conda --version  # conda 25.5.1
python --version  # Python 3.12.8
```

### 第二步：项目代码获取

#### Git环境配置
```bash
# Git版本
git --version  # git version 2.47.1

# 全局配置
git config --global user.name "yanghanggit"
git config --global user.email "yanghanggit@163.com"

# 克隆项目
git clone https://github.com/xiaomenghuan511/nirva_service.git
```

### 第三步：跨平台兼容性问题解决

#### 🔍 问题发现

**核心问题**：原始`environment.yml`包含macOS ARM64特定构建标识符

```yaml
# 问题示例
dependencies:
  - asyncpg=0.29.0=py312h80987f9_0  # ❌ ARM64特定构建
  - psycopg2=2.9.10=py312h80987f9_0 # ❌ ARM64特定构建
```

**错误现象**：
```bash
conda env create -f environment.yml
# ResolvePackageNotFound: 
# - asyncpg=0.29.0=py312h80987f9_0
# - psycopg2=2.9.10=py312h80987f9_0
```

#### 🛠️ 解决方案实施

**1. environment.yml修复**

移除平台特定构建标识符：
```yaml
# 修复前
- asyncpg=0.29.0=py312h80987f9_0

# 修复后  
- asyncpg=0.29.0
```

**2. requirements.txt版本标准化**

```python
# 关键更新
redis==6.2.0                    # 明确版本
uvicorn[standard]==0.27.1        # 添加可选依赖
python-jose[cryptography]==3.4.0 # 指定加密后端
passlib[bcrypt]==1.7.4           # 指定哈希后端
```

**3. 创建Linux优化版本**

生成`environment-linux.yml`作为备份：
```bash
conda env export --no-builds > environment-linux.yml
```

#### ✅ 验证结果

```bash
# 干运行测试
conda env create -f environment.yml --dry-run
# ✅ 成功：Collecting package metadata completed

# 实际创建环境
conda env create -f environment.yml
# ✅ 成功：nirva环境创建完成
```

### 第四步：Git工作流建立

#### 代码提交
```bash
# 暂存修改
git add environment.yml requirements.txt environment-linux.yml

# 提交更改
git commit -m "feat: Fix cross-platform compatibility for environment files"
# 提交ID: aef97ec
```

#### GitHub认证解决

**问题**：Fine-grained Token在协作仓库中权限不足
```bash
git push origin main
# remote: Permission to xiaomenghuan511/nirva_service.git denied to yanghanggit
```

**解决**：使用Classic Personal Access Token
- 权限设置：repo + workflow
- 成功推送：`aef97ec` → `origin/main`

## 📊 技术细节总结

### 依赖管理优化

| 组件 | 修复前 | 修复后 | 改进点 |
|------|--------|--------|--------|
| asyncpg | `=py312h80987f9_0` | `=0.29.0` | 移除ARM64构建标识 |
| psycopg2 | `=py312h80987f9_0` | `=2.9.10` | 跨平台兼容 |
| redis | 无版本 | `==6.2.0` | 版本明确化 |
| uvicorn | `==0.27.1` | `[standard]==0.27.1` | 添加可选依赖 |

### 文件结构优化

```text
nirva_service/
├── environment.yml          # ✅ 跨平台兼容版本
├── requirements.txt         # ✅ 版本标准化
├── environment-linux.yml    # ✅ Linux优化备份
└── docs/
    ├── 日志1:AWS_EC2_FastAPI部署实战记录.md
    ├── 日志3:AWS_EC2_项目部署与环境同步实战.md  # 🆕 本文档
    └── ENVIRONMENT_SYNC_REPORT.md  # 📝 详细技术报告
```

## 💡 最佳实践总结

### 跨平台开发

1. **环境文件标准化**
   - 避免平台特定构建标识符
   - 使用`--no-builds`导出通用环境
   - 维护多平台版本备份

2. **版本管理规范**
   - 明确指定依赖版本
   - 使用可选依赖语法
   - 定期同步requirements.txt

### Git协作流程

1. **权限管理**
   - 协作仓库使用Classic Token
   - Fine-grained Token适用于个人仓库
   - 合理配置Token权限范围

2. **提交规范**
   - 使用语义化提交信息
   - 合理组织提交粒度
   - 及时推送重要更改

### AWS服务选型

1. **托管vs自建权衡**
   - 托管服务：高可用、自动备份、免维护
   - 自建服务：成本更低、完全控制
   - 生产环境优先选择托管服务

## 🎓 关键学习收获

### 技术能力提升
- [x] 掌握conda跨平台环境管理
- [x] 学会处理平台兼容性问题
- [x] 熟悉Git协作工作流
- [x] 理解AWS托管服务优势

### 问题解决思路
- [x] 系统性排查环境问题根因
- [x] 制定分步骤解决方案
- [x] 建立验证和回滚机制
- [x] 完善文档记录流程

### 云原生理念建立
- [x] 理解托管服务的价值
- [x] 掌握云端开发的最佳实践
- [x] 认识基础设施即代码的重要性

## 📈 下一步规划

### 即将实施
1. **AWS RDS PostgreSQL配置**
   - 创建数据库实例
   - 配置安全组和访问权限
   - 更新应用数据库连接

2. **AWS ElastiCache Redis部署**
   - 选择合适的节点类型
   - 配置集群模式
   - 集成到FastAPI应用

3. **应用完整部署测试**
   - 环境变量配置
   - 服务启动验证
   - 端到端功能测试

### 后续优化方向
- 容器化部署（Docker + ECS）
- CI/CD管道搭建
- 监控和日志系统
- 负载均衡和高可用架构

## 🏆 项目成果

本次部署实战成功实现了：

1. **跨平台兼容性解决** - 从macOS开发环境到Linux生产环境的无缝迁移
2. **标准化工作流建立** - Git协作、环境管理、文档记录的规范化
3. **技术选型优化** - 选择AWS托管服务，为后续扩展打下基础
4. **问题解决能力提升** - 系统性排查和解决复杂技术问题

这为后续的AWS托管服务集成和生产环境优化奠定了坚实的基础。

---

**下次目标**: 完成AWS RDS和ElastiCache的配置，实现完整的云原生架构部署。
