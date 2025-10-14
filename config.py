"""
配置文件
"""
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# Telegram Bot 配置
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# LLM API 配置
LLM_API_KEY = os.getenv("LLM_API_KEY")
LLM_API_BASE = os.getenv("LLM_API_BASE", "https://api.openai.com/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")

# 垃圾消息检测配置
CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.7"))

# 管理员用户 ID（不会被踢出）
ADMIN_USER_IDS_STR = os.getenv("ADMIN_USER_IDS", "")
ADMIN_USER_IDS = [int(uid.strip()) for uid in ADMIN_USER_IDS_STR.split(",") if uid.strip()]

# 日志配置
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# LLM 提示词模板
SPAM_DETECTION_PROMPT = """你是一个专业的垃圾消息检测助手。请分析以下消息内容，判断它是否为垃圾消息、广告或恶意内容。

需要检测的消息内容：
```
{message_text}
```

发送者信息：
- 用户名: {username}
- 用户 ID: {user_id}
- 是否为新成员: {is_new_member}

请根据以下标准判断：
1. 是否包含明显的广告推广内容
2. 是否包含诈骗、钓鱼链接
3. 是否为重复发送的垃圾信息
4. 是否包含不当内容（色情、暴力、违法信息等）
    色情消息如：
    - 女生喊，不要艹我了，我有男朋友了
    - 看着女友被 艹
    含有"艹"字、"操比"、"肏"、"肏屄"等等字眼
5. 是否为恶意营销或拉群信息
6. 是否包含大量无关链接或联系方式
7. ⚠️ 【重点】是否为频道转发消息（消息中包含 [转发自频道] 标记）- 这通常是广告
8. ⚠️ 【重点】是否包含 Telegram 频道/群组链接（t.me/ 或 telegram.me/）- 这通常是引流
9. 是否包含引导加入其他群组/频道的内容

特别注意：
- 如果消息是从其他频道转发来的，大概率是广告/诈骗，置信度应该很高（>0.8）
- 如果消息包含 t.me/ 或 telegram.me/ 链接，大概率是引流广告，置信度应该很高（>0.8）
- 频道转发 + Telegram 链接的组合，几乎100%是垃圾消息

请以 JSON 格式回复，包含以下字段：
- is_spam: true 或 false（是否为垃圾消息）
- confidence: 0.0-1.0（置信度）
- reason: 判断理由（简短说明）
- category: 垃圾消息类型（如果是垃圾消息，可选：advertisement、scam、repetitive、inappropriate、marketing、channel_spam、other）

只返回 JSON，不要其他内容。

示例回复格式：
{{
  "is_spam": true,
  "confidence": 0.95,
  "reason": "包含明显的商业广告和推广内容",
  "category": "advertisement"
}}
"""

# 验证必需的配置
def validate_config():
    """验证配置是否完整"""
    errors = []
    
    if not TELEGRAM_BOT_TOKEN:
        errors.append("未设置 TELEGRAM_BOT_TOKEN")
    
    if not LLM_API_KEY:
        errors.append("未设置 LLM_API_KEY")
    
    if errors:
        raise ValueError(f"配置错误:\n" + "\n".join(f"- {err}" for err in errors))
    
    return True
