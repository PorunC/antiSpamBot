# Telegram 垃圾消息过滤机器人

这是一个使用 LLM API 来自动检测和删除 Telegram 群组中垃圾消息和广告的机器人。

## 功能特点

- 🤖 实时监听群组消息
- 🧠 使用 LLM (如 OpenAI GPT/Claude/国内大模型) 智能判断消息是否为垃圾内容
- 🗑️ 自动删除垃圾消息
- 👮 自动踢出发送垃圾消息的成员
- ⚙️ 可配置的过滤规则
- 📊 日志记录功能

## 安装步骤

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

复制 `.env.example` 文件为 `.env`:

```bash
cp .env.example .env
```

然后编辑 `.env` 文件，填入以下信息：

- `TELEGRAM_BOT_TOKEN`: 从 [@BotFather](https://t.me/botfather) 获取的机器人 Token
- `LLM_API_KEY`: 你的 LLM API 密钥
- `LLM_API_BASE`: LLM API 的基础 URL
- `LLM_MODEL`: 使用的模型名称

### 3. 获取 Telegram Bot Token

1. 在 Telegram 中找到 [@BotFather](https://t.me/botfather)
2. 发送 `/newbot` 命令创建新机器人
3. 按照提示设置机器人名称和用户名
4. 保存获得的 Token

### 4. 设置机器人权限

将机器人添加到你的群组，并授予以下权限：
- ✅ 删除消息
- ✅ 封禁用户

## 使用方法

### 启动机器人

```bash
python bot.py
```

### 机器人命令

- `/start` - 开始使用机器人
- `/help` - 显示帮助信息
- `/status` - 查看机器人状态

## 配置说明

在 `config.py` 中可以调整以下配置：

- `SPAM_DETECTION_PROMPT`: 用于 LLM 判断的提示词模板
- `CONFIDENCE_THRESHOLD`: 判断为垃圾消息的置信度阈值
- `ADMIN_USER_IDS`: 管理员用户 ID 列表（不会被踢出）

## 项目结构

```
bot/
├── bot.py              # 主程序文件
├── config.py           # 配置文件
├── llm_api.py         # LLM API 调用模块
├── spam_detector.py   # 垃圾消息检测模块
├── requirements.txt   # Python 依赖
├── .env.example      # 环境变量示例
└── README.md         # 说明文档
```

## 注意事项

1. ⚠️ 确保机器人在群组中有管理员权限
2. ⚠️ 建议先在测试群组中测试
3. ⚠️ 注意 LLM API 调用成本
4. ⚠️ 可以设置管理员白名单，避免误判

## 安全建议

- 不要将 `.env` 文件提交到版本控制系统
- 定期检查机器人的判断准确性
- 保留操作日志以便审查

## 许可证

MIT License
