"""
配置文件
"""
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# Telegram Bot 配置
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# 代理配置（可选，如果在中国大陆需要配置）
# 格式: http://host:port 或 socks5://host:port
PROXY_URL = os.getenv("PROXY_URL", None)

# LLM API 配置
LLM_API_KEY = os.getenv("LLM_API_KEY")
LLM_API_BASE = os.getenv("LLM_API_BASE", "https://api.openai.com/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")

# 垃圾消息检测配置
CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.7"))

# 管理员用户 ID（不会被踢出）
ADMIN_USER_IDS_STR = os.getenv("ADMIN_USER_IDS", "")
ADMIN_USER_IDS = [int(uid.strip()) for uid in ADMIN_USER_IDS_STR.split(",") if uid.strip()]

# 系统白名单用户 ID（Telegram 官方账号等，不进行检测）
# 777000 是 Telegram 官方服务消息账号
# 1087968824 是 GroupAnonymousBot（群组匿名机器人，用于发送匿名管理员消息）
SYSTEM_USER_IDS = [777000, 1087968824]

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

自动风险评估：
{risk_indicators}

请根据以下标准判断：
1. 是否包含明显的广告推广内容
2. 是否包含诈骗、钓鱼链接
3. 是否为重复发送的垃圾信息
4. 是否包含不当内容（色情、暴力、违法信息等）
    色情消息如：
    - 女生喊，不要艹我了，我有男朋友了
    - 看着女友被 艹
    - 被艹、嫖娼、襙逼、被一堆人玩、艹、艹我
    - 双马尾当方向盘
    - 揪着双马尾后入
    - 大熊、大胸
    含有"艹"字、"操比"、"肏"、"肏屄"等等字眼
5. 是否为恶意营销或拉群信息
    - 兼职、假钞、假币、假鈔、油卡、e卡
    - 兼职、线上做、报酬、预萯、副业
    - 零成本、解冻、@、户籍、快递、查档、项目、风险
    - 贷款、信用卡、分期、利息、额度
    - 代还、还款、套现、提现、秒批、秒下
    - 带单、多空双吃、拿下利润


6. 用户昵称是否属于引流打广告
    引流用户昵称如：
    - UW👆飛机会员开通 3.3U 限今天最低价☄️EF 
    - UF✌️小飞机会员激活 2.7U 官保💪QO

7. ⚠️ 【重点】是否为频道转发消息（消息中包含【⚠️ 转发消息】标记）- 这通常是广告
8. ⚠️ 【重点】是否包含 Telegram 频道/群组链接（消息中包含【⚠️ Telegram 频道/群组链接】标记）- 这通常是引流
9. 是否包含引导加入其他群组/频道的内容
10. 是否包含消息按钮（消息中包含【⚠️ 消息按钮】标记）- 常见于广告
11. 是否包含联系人信息（消息中包含【⚠️ 联系人信息】标记）- 常见于引流

特别注意：
- 如果消息**本身**是从其他频道转发来的，大概率是广告/诈骗，置信度应该很高（>0.8）
- 如果消息包含 Telegram 频道/群组链接，大概率是引流广告，置信度应该很高（>0.8）
- 频道转发 + Telegram 链接的组合，几乎100%是垃圾消息（置信度 >0.95）
- 如果自动风险评估的风险分数 > 0.6，应该提高警惕
- 包含消息按钮的转发消息，几乎都是广告

⚠️ 【回复消息的判断规则】：
- 如果消息是回复类型，请同时分析【用户发送的内容】和【被回复的消息内容】
- 普通的聊天回复（如"好的"、"谢谢"、"👍"、表情等）不应该被判定为垃圾消息
- 即使回复的是转发消息或广告，如果用户的回复本身是正常聊天，也不应封禁
- 但如果用户在回复中包含引流链接、联系方式、广告等，仍然应该判定为垃圾
- 需要结合上下文判断：用户回复是在正常讨论，还是在配合发广告

🔴 【回复白名单用户的特殊规则 - 极其重要】：
- 如果消息显示"用户正在回复白名单用户"，说明被回复的是管理员或系统白名单用户
- 这种情况下，你**不会看到被回复消息的内容**，因为已经被系统过滤
- 请**只根据用户发送的回复内容本身**进行判断
- **绝对不要**推测被回复消息的内容，也不要因为某些词语可能与不当内容相关就判定为垃圾
- **只有**当前用户的回复内容**明确包含**以下内容时才判定为垃圾：
  * 明确的广告链接（t.me/、telegram.me/等）
  * 明确的联系方式（电话、微信号等）
  * 明确的色情、暴力、违法内容描述
  * 明确的引流、拉群、推广行为
- 白名单用户可能会分享各种内容供讨论，普通用户回复是正常社交行为

必须封禁的回复：
❌ "加我 t.me/xxx" " @xxx" 某个用户 - 明确的引流
❌ 包含色情描述的长文本 - 明确的不当内容
❌ 包含广告链接 - 明确的广告


请以 JSON 格式回复，包含以下字段：
- is_spam: true 或 false（是否为垃圾消息）
- confidence: 0.0-1.0（置信度）
- reason: 判断理由（简短说明）
- category: 垃圾消息类型（如果是垃圾消息，可选：advertisement、scam、repetitive、inappropriate、marketing、channel_spam、phishing、contact_spam、other）

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
