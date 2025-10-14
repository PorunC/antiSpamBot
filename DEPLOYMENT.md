# 部署指南

本文档介绍如何在不同环境中部署 Telegram 垃圾消息过滤机器人。

## 目录

- [本地开发环境](#本地开发环境)
- [Linux 服务器部署](#linux-服务器部署)
- [Docker 部署](#docker-部署)
- [云服务部署](#云服务部署)
- [监控和维护](#监控和维护)

## 本地开发环境

### 前置要求

- Python 3.8 或更高版本
- pip 包管理器
- Git（可选）

### 快速开始

```bash
# 克隆或下载项目
cd bot

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 文件填入配置

# 运行机器人
python bot.py
```

## Linux 服务器部署

### 使用 systemd（推荐）

#### 1. 创建服务文件

```bash
sudo nano /etc/systemd/system/telegram-spam-filter.service
```

内容：

```ini
[Unit]
Description=Telegram Spam Filter Bot
After=network.target

[Service]
Type=simple
User=你的用户名
WorkingDirectory=/home/你的用户名/bot
Environment="PATH=/home/你的用户名/bot/venv/bin"
ExecStart=/home/你的用户名/bot/venv/bin/python /home/你的用户名/bot/bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

#### 2. 启动服务

```bash
# 重载 systemd
sudo systemctl daemon-reload

# 启用服务（开机自启）
sudo systemctl enable telegram-spam-filter

# 启动服务
sudo systemctl start telegram-spam-filter

# 查看状态
sudo systemctl status telegram-spam-filter

# 查看日志
sudo journalctl -u telegram-spam-filter -f
```

#### 3. 管理服务

```bash
# 停止服务
sudo systemctl stop telegram-spam-filter

# 重启服务
sudo systemctl restart telegram-spam-filter

# 禁用开机自启
sudo systemctl disable telegram-spam-filter
```

### 使用 screen 或 tmux

#### Screen

```bash
# 创建新 session
screen -S telegram_bot

# 激活虚拟环境并运行
cd /path/to/bot
source venv/bin/activate
python bot.py

# 分离 session: Ctrl+A 然后按 D
# 重新连接: screen -r telegram_bot
# 列出所有 session: screen -ls
# 杀死 session: screen -X -S telegram_bot quit
```

#### Tmux

```bash
# 创建新 session
tmux new -s telegram_bot

# 运行机器人
cd /path/to/bot
source venv/bin/activate
python bot.py

# 分离 session: Ctrl+B 然后按 D
# 重新连接: tmux attach -t telegram_bot
# 列出所有 session: tmux ls
# 杀死 session: tmux kill-session -t telegram_bot
```

## Docker 部署

### 1. 创建 Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目文件
COPY . .

# 运行机器人
CMD ["python", "bot.py"]
```

### 2. 创建 docker-compose.yml

```yaml
version: '3.8'

services:
  telegram-bot:
    build: .
    restart: unless-stopped
    env_file:
      - .env
    volumes:
      - ./logs:/app/logs
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

### 3. 构建和运行

```bash
# 构建镜像
docker-compose build

# 启动容器
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止容器
docker-compose down

# 重启容器
docker-compose restart
```

## 云服务部署

### AWS EC2

1. 创建 EC2 实例（推荐 t3.micro 或更高）
2. 连接到实例：
   ```bash
   ssh -i your-key.pem ubuntu@your-instance-ip
   ```
3. 安装 Python 和依赖：
   ```bash
   sudo apt update
   sudo apt install python3 python3-pip python3-venv git -y
   ```
4. 克隆项目并按照 Linux 部署步骤操作

### 阿里云 ECS

1. 创建 ECS 实例
2. 配置安全组（开放必要端口）
3. 按照 Linux 部署步骤操作

### 腾讯云轻量应用服务器

1. 创建轻量应用服务器
2. 选择 Ubuntu 系统
3. 按照 Linux 部署步骤操作

### Heroku（免费层）

1. 创建 `Procfile`:
   ```
   worker: python bot.py
   ```

2. 创建 `runtime.txt`:
   ```
   python-3.11.0
   ```

3. 部署：
   ```bash
   heroku login
   heroku create your-bot-name
   heroku config:set TELEGRAM_BOT_TOKEN=your_token
   heroku config:set LLM_API_KEY=your_key
   # ... 设置其他环境变量
   git push heroku main
   heroku ps:scale worker=1
   heroku logs --tail
   ```

### Railway（推荐）

1. 在 Railway 创建新项目
2. 连接 GitHub 仓库
3. 在设置中添加环境变量
4. 自动部署

## 监控和维护

### 日志管理

#### 1. 配置日志文件

修改 `bot.py`：

```python
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
```

#### 2. 日志轮转（logrotate）

创建 `/etc/logrotate.d/telegram-bot`:

```
/path/to/bot/bot.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 644 your_user your_user
}
```

### 监控脚本

创建 `monitor.sh`:

```bash
#!/bin/bash

SERVICE_NAME="telegram-spam-filter"
EMAIL="your@email.com"

if ! systemctl is-active --quiet $SERVICE_NAME; then
    echo "Service $SERVICE_NAME is not running! Restarting..." | mail -s "Bot Alert" $EMAIL
    systemctl start $SERVICE_NAME
fi
```

添加到 crontab（每 5 分钟检查一次）：

```bash
crontab -e
# 添加：
*/5 * * * * /path/to/monitor.sh
```

### 性能监控

使用 `htop` 或 `top` 监控资源使用：

```bash
# 安装 htop
sudo apt install htop

# 运行
htop
```

### 健康检查

创建 `health_check.py`:

```python
import asyncio
from telegram import Bot
import config

async def check_health():
    try:
        bot = Bot(token=config.TELEGRAM_BOT_TOKEN)
        me = await bot.get_me()
        print(f"✅ Bot is running: @{me.username}")
        return True
    except Exception as e:
        print(f"❌ Bot check failed: {e}")
        return False

if __name__ == '__main__':
    asyncio.run(check_health())
```

### 自动备份配置

```bash
#!/bin/bash
# backup.sh

BACKUP_DIR="/path/to/backups"
DATE=$(date +%Y%m%d_%H%M%S)

# 备份 .env 文件
cp /path/to/bot/.env "$BACKUP_DIR/env_$DATE.backup"

# 保留最近 7 天的备份
find $BACKUP_DIR -name "env_*.backup" -mtime +7 -delete

echo "Backup completed: $DATE"
```

添加到 crontab（每天凌晨 2 点备份）：

```bash
0 2 * * * /path/to/backup.sh
```

## 故障排除

### 机器人无响应

1. 检查服务状态：
   ```bash
   sudo systemctl status telegram-spam-filter
   ```

2. 查看日志：
   ```bash
   sudo journalctl -u telegram-spam-filter -n 100
   ```

3. 检查网络连接：
   ```bash
   ping api.telegram.org
   ```

### 权限问题

确保机器人是群组管理员：
```bash
# 使用 health_check.py 验证
python health_check.py
```

### API 限流

如果遇到 API 限流，可以添加重试逻辑或调整请求频率。

### 内存占用过高

1. 检查内存使用：
   ```bash
   ps aux | grep python
   ```

2. 优化代码或增加服务器内存

## 安全建议

1. **使用防火墙**：
   ```bash
   sudo ufw enable
   sudo ufw allow ssh
   ```

2. **定期更新系统**：
   ```bash
   sudo apt update && sudo apt upgrade -y
   ```

3. **使用 SSH 密钥**而非密码登录

4. **限制 sudo 权限**

5. **定期备份** .env 文件和配置

6. **监控日志**以发现异常活动

## 性能优化

1. **使用 Redis 缓存**（可选）：
   - 缓存用户信息
   - 减少重复 API 调用

2. **批量处理**：
   - 对消息进行批量分析

3. **异步处理**：
   - 使用异步 I/O
   - 并发处理多个消息

4. **数据库**（可选）：
   - 记录处理历史
   - 统计分析

## 更新和维护

### 更新代码

```bash
# 停止服务
sudo systemctl stop telegram-spam-filter

# 备份当前版本
cp -r /path/to/bot /path/to/bot.backup

# 拉取最新代码
cd /path/to/bot
git pull

# 更新依赖
source venv/bin/activate
pip install -r requirements.txt

# 重启服务
sudo systemctl start telegram-spam-filter
```

### 回滚

```bash
# 停止服务
sudo systemctl stop telegram-spam-filter

# 恢复备份
rm -rf /path/to/bot
mv /path/to/bot.backup /path/to/bot

# 重启服务
sudo systemctl start telegram-spam-filter
```

## 支持

如有问题，请查看日志文件或联系技术支持。
