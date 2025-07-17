# 日志4：AWS EC2 Linux 环境数据库安装配置

**日期**: 2025年7月17日  
**环境**: AWS EC2 - Amazon Linux 2023  
**目标**: 在 EC2 Linux 服务器上安装和配置 Redis 与 PostgreSQL

---

## 📋 背景与目标

### 开发环境架构
- **本地开发**: MacBook Pro (macOS) + conda 环境
- **远程服务器**: AWS EC2 Linux (Amazon Linux 2023)
- **访问方式**: VSCode Remote SSH
- **项目**: nirva_service (Python 纯项目)

### 版本要求（根据 README.md）
- **Redis**: 8.0.1 (macbook 本地版本)
- **PostgreSQL**: 14.18 (macbook 本地版本)

---

## 🚀 实施过程

### 阶段1：Git 同步
**目标**: 确保 EC2 上的代码与 origin 同步

```bash
# 检查当前分支状态
git status
git branch -a

# 发现远程分支领先 3 个提交
git fetch origin
git log --oneline HEAD..origin/yh-aws-ec2-linux

# 执行同步
git pull origin yh-aws-ec2-linux
```

**结果**: 
- ✅ 成功同步，Fast-forward 合并
- ✅ 获得最新的测试脚本 `run_dev_clear_db.py`

### 阶段2：Redis 安装
**系统环境**: Amazon Linux 2023

```bash
# 查找可用版本
sudo dnf search redis

# 安装 Redis 6
sudo dnf install -y redis6

# 启动服务
sudo systemctl start redis6
sudo systemctl enable redis6

# 验证安装
redis6-cli --version  # redis-cli 6.2.14
redis6-cli ping        # PONG
```

**配置特点**:
- ✅ 无密码认证（符合项目配置）
- ✅ 绑定 127.0.0.1:6379（仅本机访问）
- ✅ 默认配置，无需额外配置文件修改

### 阶段3：PostgreSQL 安装
**挑战**: Amazon Linux 2023 提供多个版本（15、16、17）

```bash
# 选择安装 PostgreSQL 15（接近目标版本 14）
sudo dnf install -y postgresql15-server postgresql15

# 初始化数据库
sudo /usr/bin/postgresql-setup --initdb

# 启动服务
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

**数据库配置**:
```bash
# 创建用户和数据库（根据项目配置）
sudo -u postgres psql -c "CREATE USER fastapi_user WITH PASSWORD '123456';"
sudo -u postgres psql -c "CREATE DATABASE my_fastapi_db OWNER fastapi_user;"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE my_fastapi_db TO fastapi_user;"
```

**认证配置**:
```bash
# 修改 pg_hba.conf 启用密码认证
sudo sed -i 's/local   all             all                                     peer/local   all             all                                     md5/' /var/lib/pgsql/data/pg_hba.conf
sudo sed -i 's/host    all             all             127.0.0.1\/32            ident/host    all             all             127.0.0.1\/32            md5/' /var/lib/pgsql/data/pg_hba.conf

# 重启服务应用配置
sudo systemctl restart postgresql
```

---

## 🔧 项目配置对应

### Redis 配置 (configuration.py)
```python
@final
class RedisConfig(BaseModel):
    host: str = "localhost"     # ✅ 匹配
    port: int = 6379           # ✅ 匹配  
    db: int = 0                # ✅ 匹配
```

### PostgreSQL 配置 (configuration.py)
```python
postgres_password: Final[str] = "123456"  # ✅ 匹配
POSTGRES_DATABASE_URL: Final[str] = (
    f"postgresql://fastapi_user:{postgres_password}@localhost/my_fastapi_db"
)  # ✅ 完全匹配
```

---

## ✅ 验证测试

### 测试脚本执行
使用项目自带的 `scripts/run_dev_clear_db.py` 进行完整测试：

**Redis 测试结果**:
```
✅ Redis 连接测试成功! 读取到的值: hello_redis_2025
✅ 测试数据清理成功!
🎉 Redis 连接和基本操作测试全部通过!
```

**PostgreSQL 测试结果**:
```
✅ PostgreSQL 数据库连接成功!
✅ 用户创建成功! 用户ID: fd3260d9-a0d7-4029-8a07-12dd081b7963
✅ 用户查询成功! 显示名: Test User PostgreSQL
✅ 用户存在性检查通过!
✅ 测试数据清理成功!
✅ 测试数据清理验证通过!
🎉 PostgreSQL 连接和基本操作测试全部通过!
```

### 功能验证
- ✅ 数据库清理和重建功能正常
- ✅ 测试用户创建成功
- ✅ 所有 CRUD 操作正常

---

## 📊 最终状态

### 已安装版本
- **Redis**: 6.2.14 (vs 目标 8.0.1)
- **PostgreSQL**: 15.13 (vs 目标 14.18)

### 服务状态
```bash
# Redis
● redis6.service - Redis persistent key-value database
     Active: active (running)
     Enabled: enabled

# PostgreSQL  
● postgresql.service - PostgreSQL database server
     Active: active (running)
     Enabled: enabled
```

### 连接测试
```bash
# Redis
redis6-cli ping  # PONG

# PostgreSQL
PGPASSWORD='123456' psql -h localhost -U fastapi_user -d my_fastapi_db -c "SELECT current_database(), current_user;"
# my_fastapi_db | fastapi_user
```

---

## 🎯 经验总结

### 成功要素
1. **版本兼容性**: 虽然版本不完全匹配，但功能完全兼容
2. **配置一致性**: 严格按照项目配置文件进行设置
3. **认证配置**: PostgreSQL 的认证方式配置是关键
4. **测试验证**: 使用项目自带测试脚本确保集成成功

### 解决的关键问题
1. **PostgreSQL 认证**: 从 peer/ident 改为 md5 密码认证
2. **服务配置**: 正确的服务启动和自启动设置
3. **权限配置**: 用户和数据库权限的正确授予

### 开发流程验证
- ✅ MacBook 开发 → GitHub 提交 → EC2 同步 → 测试验证

---

## 📝 后续计划

1. **性能优化**: 根据实际使用情况调整数据库配置
2. **监控设置**: 添加数据库监控和日志
3. **备份策略**: 制定数据库备份和恢复方案
4. **安全加固**: 考虑生产环境的安全配置

---

**状态**: ✅ 完成  
**下一步**: 可以开始在 EC2 环境进行完整的服务部署和测试
