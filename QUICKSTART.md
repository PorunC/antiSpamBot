# 快速开始指南

## 第一步：获取 Telegram Bot Token

1. 在 Telegram 中搜索 `@BotFather`
2. 发送命令 `/newbot`
3. 按照提示设置机器人名称和用户名（例如：`MySpamFilter_bot`）
4. 保存 BotFather 发给你的 Token（格式类似：`1234567890:ABCdefGHIjklMNOpqrsTUVwxyz`）

## 第二步：获取 LLM API 密钥

你可以选择以下任一服务：

### 选项 1: OpenAI GPT
- 访问 https://platform.openai.com/api-keys
- 创建 API Key
- 配置：
  ```
  LLM_API_KEY=sk-...
  LLM_API_BASE=https://api.openai.com/v1
  LLM_MODEL=gpt-4o-mini
  ```

### 选项 2: 智谱 AI（国内）
- 访问 https://open.bigmodel.cn/
- 创建 API Key
- 配置：
  ```
  LLM_API_KEY=...
  LLM_API_BASE=https://open.bigmodel.cn/api/paas/v4
  LLM_MODEL=glm-4-flash
  ```

### 选项 3: 阿里云百炼（国内）
- 访问 https://bailian.console.aliyun.com/
- 创建 API Key
- 配置：
  ```
  LLM_API_KEY=sk-...
  LLM_API_BASE=https://dashscope.aliyuncs.com/compatible-mode/v1
  LLM_MODEL=qwen-plus
  ```

### 选项 4: DeepSeek（性价比高）
- 访问 https://platform.deepseek.com/
- 创建 API Key
- 配置：
  ```
  LLM_API_KEY=sk-...
  LLM_API_BASE=https://api.deepseek.com/v1
  LLM_MODEL=deepseek-chat
  ```

## 第三步：配置机器人

1. 复制 `.env.example` 为 `.env`：
   ```bash
   cp .env.example .env
   ```

2. 编辑 `.env` 文件：
   ```bash
   nano .env  # 或使用其他编辑器
   ```

3. 填入配置信息：
   ```env
   TELEGRAM_BOT_TOKEN=你的_Bot_Token
   LLM_API_KEY=你的_LLM_API_Key
   LLM_API_BASE=API_基础_URL
   LLM_MODEL=模型名称
   CONFIDENCE_THRESHOLD=0.7
   ADMIN_USER_IDS=你的用户ID,另一个管理员ID
   ```

## 第四步：获取你的 Telegram 用户 ID（可选）

如果你想将自己加入管理员白名单：

1. 在 Telegram 中搜索 `@userinfobot`
2. 发送 `/start`
3. 机器人会返回你的用户 ID
4. 将 ID 填入 `.env` 文件的 `ADMIN_USER_IDS`

## 第五步：安装依赖并启动

### macOS/Linux:
```bash
chmod +x start.sh
./start.sh
```

或手动安装：
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python bot.py
```

### Windows:
```cmd
start.bat
```

或手动安装：
```cmd
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python bot.py
```

## 第六步：将机器人添加到群组

1. 在群组中，点击群组名称 → 添加成员
2. 搜索你的机器人用户名并添加
3. 点击群组设置 → 管理员 → 添加管理员
4. 选择你的机器人，授予以下权限：
   - ✅ 删除消息
   - ✅ 封禁用户

## 第七步：测试机器人

1. 在群组中发送 `/start` 测试机器人是否响应
2. 发送 `/status` 查看机器人状态
3. 尝试发送一些测试消息

## 测试用例

### 正常消息（应该保留）：
- "大家好，很高兴加入这个群组"
- "今天天气不错"
- "有人在吗？"

### 垃圾消息（应该被删除）：
- "加微信 xxx 领取免费资料"
- "点击链接 xxx 获得优惠"
- "扫码进群，限时福利"
- "私聊我，有偿服务"

## 调整检测灵敏度

如果误判率太高，可以调整置信度阈值：

```env
# 默认值是 0.7（70%）
# 提高到 0.8 或 0.9 可以减少误判
CONFIDENCE_THRESHOLD=0.8
```

## 常见问题

### Q: 机器人提示权限不足
A: 确保机器人在群组中是管理员，并有删除消息和封禁用户的权限。

### Q: 机器人不响应
A: 检查 `.env` 文件配置是否正确，特别是 `TELEGRAM_BOT_TOKEN`。

### Q: LLM API 调用失败
A: 检查 `LLM_API_KEY` 和 `LLM_API_BASE` 是否正确，确认 API 额度充足。

### Q: 误判率太高
A: 调整 `CONFIDENCE_THRESHOLD` 值，或修改 `config.py` 中的 `SPAM_DETECTION_PROMPT`。

### Q: 如何查看日志
A: 机器人运行时会在控制台输出日志，你也可以重定向到文件：
```bash
python bot.py > bot.log 2>&1
```

## 后台运行（生产环境）

### 使用 screen（Linux/macOS）:
```bash
screen -S telegram_bot
source venv/bin/activate
python bot.py
# 按 Ctrl+A 然后按 D 退出 screen
# 重新连接: screen -r telegram_bot
```

### 使用 systemd（Linux）:
创建 `/etc/systemd/system/telegram-bot.service`:
```ini
[Unit]
Description=Telegram Spam Filter Bot
After=network.target

[Service]
Type=simple
User=你的用户名
WorkingDirectory=/path/to/bot
ExecStart=/path/to/bot/venv/bin/python /path/to/bot/bot.py
Restart=always

[Install]
WantedBy=multi-user.target
```

启动服务：
```bash
sudo systemctl enable telegram-bot
sudo systemctl start telegram-bot
sudo systemctl status telegram-bot
```

## 安全建议

1. ⚠️ 不要将 `.env` 文件提交到 Git 仓库
2. ⚠️ 定期检查机器人的判断准确性
3. ⚠️ 设置管理员白名单，避免误删管理员消息
4. ⚠️ 保留日志以便审查
5. ⚠️ 注意 LLM API 调用成本

## 进阶配置

### 自定义检测提示词

编辑 `config.py` 中的 `SPAM_DETECTION_PROMPT`，可以根据你的群组特点调整检测规则。

### 添加更多命令

在 `bot.py` 中可以添加更多命令处理器，例如：
- 查看统计信息
- 临时禁用/启用检测
- 白名单管理
- 等等...

## 支持与贡献

如有问题或建议，欢迎提交 Issue 或 Pull Request！
