# 项目架构说明

## 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                    Telegram Bot 架构图                        │
└─────────────────────────────────────────────────────────────┘

┌──────────────┐
│ Telegram     │
│ 群组消息     │
└──────┬───────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────┐
│                      bot.py (主程序)                          │
│  ┌────────────────────────────────────────────────────────┐  │
│  │ • 接收消息                                              │  │
│  │ • 命令处理 (/start, /help, /status)                    │  │
│  │ • 错误处理                                              │  │
│  │ • 通知管理                                              │  │
│  └────────────────────────────────────────────────────────┘  │
└────────────────────────┬─────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────┐
│              spam_detector.py (检测模块)                      │
│  ┌────────────────────────────────────────────────────────┐  │
│  │ • 消息内容提取                                          │  │
│  │ • 管理员白名单检查                                      │  │
│  │ • 新成员检测                                            │  │
│  │ • 调用 LLM 分析                                         │  │
│  │ • 判断是否删除/封禁                                     │  │
│  └────────────────────────────────────────────────────────┘  │
└────────────────────────┬─────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────┐
│                llm_api.py (LLM 调用模块)                      │
│  ┌────────────────────────────────────────────────────────┐  │
│  │ • 构建检测提示词                                        │  │
│  │ • 调用 LLM API                                          │  │
│  │ • 解析 JSON 响应                                        │  │
│  │ • 错误处理和重试                                        │  │
│  └────────────────────────────────────────────────────────┘  │
└────────────────────────┬─────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────┐
│                     LLM API 服务                              │
│  (OpenAI / Claude / 智谱 AI / DeepSeek / ...)               │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│                    config.py (配置模块)                       │
│  • 环境变量加载                                               │
│  • 配置验证                                                   │
│  • 提示词模板                                                 │
└──────────────────────────────────────────────────────────────┘
```

## 文件结构说明

```
bot/
├── 📄 核心文件
│   ├── bot.py                  # 主程序入口，处理 Telegram 消息
│   ├── config.py               # 配置管理，环境变量加载
│   ├── llm_api.py             # LLM API 调用封装
│   └── spam_detector.py       # 垃圾消息检测逻辑
│
├── 📄 配置文件
│   ├── .env.example           # 环境变量示例
│   ├── requirements.txt       # Python 依赖
│   ├── .gitignore            # Git 忽略文件
│   └── runtime.txt           # Python 运行时版本（Heroku）
│
├── 📄 Docker 相关
│   ├── Dockerfile            # Docker 镜像构建文件
│   ├── docker-compose.yml    # Docker Compose 配置
│   └── Procfile             # Heroku/Railway 部署文件
│
├── 📄 启动脚本
│   ├── start.sh             # Linux/macOS 启动脚本
│   ├── start.bat            # Windows 启动脚本
│   └── test_bot.py          # 测试脚本
│
├── 📄 文档
│   ├── README.md            # 项目介绍和基础说明
│   ├── QUICKSTART.md        # 快速开始指南
│   ├── DEPLOYMENT.md        # 部署指南
│   ├── FAQ.md              # 常见问题解答
│   ├── ARCHITECTURE.md     # 本文件，架构说明
│   └── LICENSE             # 开源许可证
│
└── 📁 运行时生成
    ├── venv/               # Python 虚拟环境
    ├── logs/              # 日志文件
    └── .env               # 实际环境变量（不提交到 Git）
```

## 数据流程

### 1. 消息接收流程

```
Telegram 群组消息
    │
    ▼
bot.py: handle_message()
    │
    ├─► 检查消息类型（群组/私聊）
    │
    ▼
spam_detector.check_message()
    │
    ├─► 检查是否为管理员 → 跳过
    ├─► 检查是否为机器人 → 跳过
    ├─► 提取消息文本
    │
    ▼
llm_api.analyze_message()
    │
    ├─► 构建提示词
    ├─► 调用 LLM API
    ├─► 解析 JSON 响应
    │
    ▼
返回检测结果
    │
    ├─► is_spam: true/false
    ├─► confidence: 0.0-1.0
    ├─► reason: 判断理由
    └─► category: 垃圾类型
    │
    ▼
bot.py: 处理结果
    │
    ├─► 如果是垃圾消息 且 置信度 >= 阈值
    │   │
    │   ├─► 删除消息
    │   ├─► 封禁用户
    │   └─► 发送通知（10秒后自动删除）
    │
    └─► 否则跳过
```

### 2. LLM API 调用流程

```
spam_detector 请求分析
    │
    ▼
llm_api.analyze_message()
    │
    ├─► 1. 构建上下文信息
    │      - 消息文本
    │      - 用户信息
    │      - 是否新成员
    │
    ├─► 2. 格式化提示词
    │      - 使用 SPAM_DETECTION_PROMPT 模板
    │      - 注入消息和用户信息
    │
    ├─► 3. 调用 OpenAI 兼容 API
    │      - POST /v1/chat/completions
    │      - 请求 JSON 格式响应
    │
    ├─► 4. 解析响应
    │      - 提取 JSON 数据
    │      - 验证必需字段
    │      - 类型转换
    │
    ├─► 5. 错误处理
    │      - API 调用失败 → 返回默认值
    │      - JSON 解析失败 → 返回默认值
    │      - 超时 → 返回默认值
    │
    └─► 返回结果
```

## 核心模块详解

### 1. bot.py - 主程序

**职责：**
- Telegram Bot 初始化和管理
- 命令处理（/start, /help, /status）
- 消息事件监听
- 执行删除和封禁操作
- 错误处理和日志记录

**关键函数：**
- `main()`: 程序入口，初始化 Bot
- `handle_message()`: 处理所有群组消息
- `start_command()`: 处理 /start 命令
- `help_command()`: 处理 /help 命令
- `status_command()`: 处理 /status 命令
- `error_handler()`: 全局错误处理

### 2. spam_detector.py - 检测模块

**职责：**
- 封装垃圾消息检测逻辑
- 管理白名单检查
- 提取和处理消息内容
- 调用 LLM 进行分析
- 返回检测结果和建议操作

**关键类/函数：**
- `SpamDetector`: 检测器类
- `check_message()`: 主检测方法
- `_extract_message_text()`: 提取消息文本
- `_is_new_member_message()`: 判断是否为新成员

### 3. llm_api.py - LLM 调用模块

**职责：**
- 封装 LLM API 调用
- 构建和格式化提示词
- 处理 API 响应
- 错误处理和降级

**关键类/函数：**
- `LLMClient`: LLM 客户端类
- `analyze_message()`: 分析消息方法
- `_get_default_result()`: 获取默认结果（失败时）

### 4. config.py - 配置模块

**职责：**
- 加载环境变量
- 定义配置常量
- 提示词模板管理
- 配置验证

**关键配置：**
- `TELEGRAM_BOT_TOKEN`: Bot Token
- `LLM_API_KEY`: LLM API 密钥
- `LLM_MODEL`: 使用的模型
- `CONFIDENCE_THRESHOLD`: 置信度阈值
- `SPAM_DETECTION_PROMPT`: 检测提示词

## 扩展点

### 1. 添加新的检测规则

在 `spam_detector.py` 中添加预检测逻辑：

```python
def check_message(self, message: Message):
    # 添加关键词黑名单检查
    if self._check_blacklist(message_text):
        return {
            "should_delete": True,
            "should_ban": True,
            "result": {"reason": "命中黑名单"},
            "skip_reason": None
        }
    
    # 继续 LLM 检测...
```

### 2. 添加数据库记录

创建 `database.py`：

```python
import sqlite3

class Database:
    def log_detection(self, user_id, is_spam, confidence):
        # 记录检测结果
        pass
    
    def get_statistics(self):
        # 获取统计信息
        pass
```

### 3. 添加 Web 管理界面

使用 Flask 或 FastAPI 创建管理面板：

```python
from flask import Flask, render_template

app = Flask(__name__)

@app.route('/dashboard')
def dashboard():
    # 显示统计信息
    pass
```

### 4. 添加图片内容检测

使用 OCR 或图片分类模型：

```python
async def analyze_image(self, image_file):
    # 使用 GPT-4V 或其他视觉模型
    pass
```

### 5. 添加用户行为分析

分析用户历史行为：

```python
class UserBehaviorAnalyzer:
    def analyze_pattern(self, user_id):
        # 分析用户行为模式
        pass
```

## 性能优化建议

### 1. 缓存机制

```python
from functools import lru_cache

@lru_cache(maxsize=1000)
def get_user_status(user_id):
    # 缓存用户状态
    pass
```

### 2. 批量处理

```python
async def batch_analyze(messages):
    # 批量分析多条消息
    tasks = [analyze_message(msg) for msg in messages]
    results = await asyncio.gather(*tasks)
    return results
```

### 3. 预过滤

在调用 LLM 前进行简单过滤：

```python
def quick_check(message_text):
    # 使用正则表达式快速检测明显的垃圾消息
    spam_patterns = [
        r'加微信.*领取',
        r'点击链接.*优惠',
        # ...
    ]
    return any(re.search(p, message_text) for p in spam_patterns)
```

## 安全考虑

### 1. 输入验证

- 验证消息长度
- 过滤特殊字符
- 防止注入攻击

### 2. 权限检查

- 验证 Bot 权限
- 检查用户权限
- 管理员白名单

### 3. API 密钥保护

- 使用环境变量
- 不提交到版本控制
- 定期轮换密钥

### 4. 速率限制

- 限制 API 调用频率
- 防止滥用
- 实现重试机制

## 监控和日志

### 1. 日志级别

- DEBUG: 详细调试信息
- INFO: 一般信息（默认）
- WARNING: 警告信息
- ERROR: 错误信息

### 2. 关键指标

- 消息处理速度
- LLM API 调用成功率
- 检测准确率
- 错误率

### 3. 告警机制

- API 调用失败
- 权限不足
- 服务异常

## 测试策略

### 1. 单元测试

测试各个模块的功能：

```python
# test_spam_detector.py
def test_extract_message_text():
    # 测试消息文本提取
    pass
```

### 2. 集成测试

测试模块间的交互：

```python
# test_integration.py
async def test_full_detection_flow():
    # 测试完整检测流程
    pass
```

### 3. 端到端测试

使用真实 Telegram 消息测试：

```bash
python test_bot.py
```

## 未来改进方向

1. **多语言支持**: 支持检测多种语言的垃圾消息
2. **自学习**: 根据反馈自动优化检测规则
3. **可视化面板**: Web 界面查看统计和配置
4. **更多检测维度**: 图片、视频、链接内容
5. **分布式部署**: 支持多实例、负载均衡
6. **插件系统**: 允许用户自定义检测插件

---

**贡献代码？** 欢迎提交 Pull Request！
