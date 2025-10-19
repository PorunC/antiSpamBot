"""
Telegram 垃圾消息过滤机器人主程序
"""
import re
import logging
import sys
import asyncio
import json
from datetime import time, datetime
from pathlib import Path
from typing import Optional, Dict, Any
from telegram import Update, BotCommand
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes
)
from telegram.error import TelegramError
import config
from llm_api import llm_client
from spam_detector import spam_detector
from log_analyzer import get_recent_ban_stats, get_total_log_stats, BEIJING_TZ

# 配置日志
log_handlers = [logging.StreamHandler(sys.stdout)]
if config.LOG_FILE:
    log_path = Path(config.LOG_FILE)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_handlers.append(logging.FileHandler(log_path, encoding="utf-8"))

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=getattr(logging, config.LOG_LEVEL),
    handlers=log_handlers,
    force=True
)
logging.getLogger("httpx").setLevel(logging.WARNING)  # Reduce noise from polling requests
logging.getLogger("httpcore").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

COMPILED_USERNAME_BLACKLIST_PATTERNS = [
    (re.compile(entry["pattern"], re.IGNORECASE), entry["reason"])
    for entry in getattr(config, "USERNAME_BLACKLIST_PATTERNS", [])
]
COMPILED_DISPLAY_NAME_BLACKLIST_PATTERNS = [
    (re.compile(entry["pattern"]), entry["reason"])
    for entry in getattr(config, "DISPLAY_NAME_BLACKLIST_PATTERNS", [])
]

CATEGORY_LABELS = {
    "username_blacklist": "本地黑名单用户名",
    "display_name_blacklist": "本地黑名单昵称",
    "username_llm_violation": "AI 判定违规用户名",
    "message_violation": "垃圾消息",
    "legacy_message_violation": "垃圾消息",
    "spam": "垃圾消息",
    "ad": "广告消息",
    "promotion": "引流推广消息",
    "scam": "诈骗/钓鱼消息",
    "other": "其他违规消息",
}


def describe_ban_category(category: Optional[str]) -> str:
    """将封禁类别转换为更易读的描述。"""
    if not category:
        return "未分类"
    if not isinstance(category, str):
        category = str(category)
    lookup_key = category.lower()
    if lookup_key in CATEGORY_LABELS:
        return CATEGORY_LABELS[lookup_key]
    return CATEGORY_LABELS.get(category, category)


def check_username_blacklist(username: str) -> Optional[str]:
    """Return blacklist match reason if username hits a local rule."""
    if not username:
        return None
    normalized = username.lstrip("@")
    for pattern, reason in COMPILED_USERNAME_BLACKLIST_PATTERNS:
        if pattern.match(normalized):
            return reason
    return None


def check_display_name_blacklist(display_name: str) -> Optional[str]:
    """Return blacklist match reason if display name hits a local rule."""
    if not display_name:
        return None
    for pattern, reason in COMPILED_DISPLAY_NAME_BLACKLIST_PATTERNS:
        if pattern.search(display_name):
            return reason
    return None


def log_ban_event(
    category: str,
    chat,
    user,
    reason: str,
    confidence: Optional[float] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> None:
    """记录统一的封禁事件日志，便于后续统计分析。"""
    event: Dict[str, Any] = {
        "category": category,
        "chat_id": getattr(chat, "id", None),
        "chat_title": getattr(chat, "title", None)
        or getattr(chat, "full_name", None)
        or getattr(chat, "first_name", None),
        "user_id": getattr(user, "id", None),
        "username": getattr(user, "username", None),
        "full_name": getattr(user, "full_name", None)
        or getattr(user, "name", None)
        or getattr(user, "first_name", None),
        "reason": reason,
    }
    if confidence is not None:
        event["confidence"] = confidence
    if extra:
        event["extra"] = extra

    try:
        payload = json.dumps(event, ensure_ascii=False, default=str)
    except (TypeError, ValueError) as exc:
        logger.warning("封禁事件序列化失败: %s", exc)
        payload = str(event)

    logger.info("BAN_EVENT %s", payload)


async def setup_bot_commands(application: Application) -> None:
    """配置机器人命令菜单，让客户端显示命令按钮。"""
    command_list = [
        BotCommand("start", "启动机器人"),
        BotCommand("help", "显示帮助信息"),
        BotCommand("status", "查看机器人状态"),
        BotCommand("banstats", "查看封禁统计"),
        BotCommand("logstats", "查看日志统计"),
    ]

    try:
        await application.bot.set_my_commands(command_list)
        logger.info("已更新机器人命令列表")
    except TelegramError as exc:
        logger.error("设置机器人命令列表失败: %s", exc)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理 /start 命令"""
    await update.message.reply_text(
        "🤖 Telegram 垃圾消息过滤机器人已启动！\n\n"
        "我会自动监测群组中的垃圾消息和广告，并进行处理。\n\n"
        "使用 /help 查看帮助信息。"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理 /help 命令"""
    help_text = """
🤖 **垃圾消息过滤机器人帮助**

**功能说明：**
- 自动检测群组中的垃圾消息和广告
- 删除检测到的垃圾消息
- 踢出发送垃圾消息的用户

**可用命令：**
/start - 启动机器人
/help - 显示此帮助信息
/status - 查看机器人状态
/logstats - 查看日志统计（管理员）

**注意事项：**
1. 机器人需要群组管理员权限才能删除消息和踢出用户
2. 管理员发送的消息不会被检测
3. 机器人使用 AI 进行判断，可能存在误判

**如有问题，请联系群组管理员。**
    """
    await update.message.reply_text(help_text, parse_mode='Markdown')


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理 /status 命令"""
    status_text = f"""
🤖 **机器人状态**

✅ 运行中
🔍 检测模型: {config.LLM_MODEL}
📊 置信度阈值: {config.CONFIDENCE_THRESHOLD}
👥 管理员白名单: {len(config.ADMIN_USER_IDS)} 人

机器人正在监听群组消息...
    """
    await update.message.reply_text(status_text, parse_mode='Markdown')


async def handle_service_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    处理系统服务消息（例如：XXX left the chat）
    自动删除这些消息以保持群组整洁
    """
    message = update.message
    
    # 只处理群组消息
    if message.chat.type not in ['group', 'supergroup']:
        return
    
    # 检查是否是 left_chat_member 消息（用户离开或被移除）
    if message.left_chat_member:
        try:
            await message.delete()
            logger.info(f"已删除系统服务消息 - 用户 {message.left_chat_member.first_name} 离开群组")
        except TelegramError as e:
            logger.debug(f"删除系统服务消息失败: {e}")

    # 检查是否是新成员加入消息
    if message.new_chat_members:
        member_display_names = []
        for member in message.new_chat_members:
            display_name = getattr(member, "full_name", None) or member.username or member.first_name or "未知用户"
            telegram_username = member.username or ""
            member_display_names.append(display_name)
            
            if member.id in config.ADMIN_USER_IDS or member.id in config.SYSTEM_USER_IDS:
                logger.debug(f"跳过用户名审核（白名单）- 用户: {display_name} (ID: {member.id})")
                continue
            
            if member.is_bot:
                logger.debug(f"跳过用户名审核（机器人）- 用户: {display_name} (ID: {member.id})")
                continue

            username_blacklist_reason = check_username_blacklist(telegram_username or "")
            if username_blacklist_reason:
                logger.warning(
                    f"检测到本地黑名单用户名 - 用户: {display_name} (ID: {member.id}), "
                    f"用户名: @{telegram_username or '无用户名'}, 理由: {username_blacklist_reason}"
                )
                try:
                    await context.bot.ban_chat_member(
                        chat_id=message.chat_id,
                        user_id=member.id
                    )
                    logger.info(f"已移除黑名单用户名用户 - {display_name} (ID: {member.id})")

                    log_ban_event(
                        category="username_blacklist",
                        chat=message.chat,
                        user=member,
                        reason=username_blacklist_reason,
                        confidence=1.0,
                        extra={
                            "trigger": "new_member",
                            "matched_username": telegram_username or None,
                        },
                    )

                    notification_lines = [
                        "🚫 检测到黑名单用户名并已移除",
                        f"👤 用户: {display_name}",
                        f"🆔 ID: {member.id}",
                        f"📛 用户名: @{telegram_username or '无用户名'}",
                        "📊 置信度: 100%",
                        f"💬 理由: {username_blacklist_reason}"
                    ]
                    notification = await context.bot.send_message(
                        chat_id=message.chat_id,
                        text="\n".join(notification_lines)
                    )

                    if context.application.job_queue:
                        context.application.job_queue.run_once(
                            delete_notification,
                            when=3,
                            data={
                                'chat_id': message.chat_id,
                                'message_id': notification.message_id
                            }
                        )
                except TelegramError as e:
                    logger.error(f"移除黑名单用户名用户失败: {e}")
                continue

            display_name_blacklist_reason = check_display_name_blacklist(display_name)
            if display_name_blacklist_reason:
                logger.warning(
                    f"检测到黑名单显示名称 - 用户: {display_name} (ID: {member.id}), 理由: {display_name_blacklist_reason}"
                )
                try:
                    await context.bot.ban_chat_member(
                        chat_id=message.chat_id,
                        user_id=member.id
                    )
                    logger.info(f"已移除黑名单显示名称用户 - {display_name} (ID: {member.id})")

                    log_ban_event(
                        category="display_name_blacklist",
                        chat=message.chat,
                        user=member,
                        reason=display_name_blacklist_reason,
                        confidence=1.0,
                        extra={
                            "trigger": "new_member",
                            "matched_display_name": display_name,
                            "matched_username": telegram_username or None,
                        },
                    )

                    notification_lines = [
                        "🚫 检测到黑名单显示名称并已移除",
                        f"👤 用户: {display_name}",
                        f"🆔 ID: {member.id}",
                        f"📛 用户名: @{telegram_username or '无用户名'}",
                        "📊 置信度: 100%",
                        f"💬 理由: {display_name_blacklist_reason}"
                    ]
                    notification = await context.bot.send_message(
                        chat_id=message.chat_id,
                        text="\n".join(notification_lines)
                    )

                    if context.application.job_queue:
                        context.application.job_queue.run_once(
                            delete_notification,
                            when=3,
                            data={
                                'chat_id': message.chat_id,
                                'message_id': notification.message_id
                            }
                        )
                except TelegramError as e:
                    logger.error(f"移除黑名单显示名称用户失败: {e}")
                continue

            join_notice = message.text or f"{display_name} 加入群聊"
            username_result = await llm_client.analyze_username(
                username=telegram_username or "",
                full_name=display_name,
                join_message=join_notice,
                user_id=member.id
            )
            
            if (
                username_result["is_violation"] and
                username_result["confidence"] >= config.USERNAME_CONFIDENCE_THRESHOLD
            ):
                logger.warning(
                    f"检测到违规用户名 - 用户: {display_name} (ID: {member.id}), "
                    f"置信度: {username_result['confidence']:.2f}, 理由: {username_result['reason']}"
                )
                try:
                    await context.bot.ban_chat_member(
                        chat_id=message.chat_id,
                        user_id=member.id
                    )
                    logger.info(f"已移除违规用户名用户 - {display_name} (ID: {member.id})")

                    log_ban_event(
                        category="username_llm_violation",
                        chat=message.chat,
                        user=member,
                        reason=username_result["reason"],
                        confidence=username_result["confidence"],
                        extra={
                            "trigger": "new_member",
                            "matched_username": telegram_username or None,
                            "analysis_category": username_result.get("category"),
                        },
                    )
                    
                    notification_lines = [
                        "🚫 检测到违规用户名并已移除",
                        f"👤 用户: {display_name}",
                        f"🆔 ID: {member.id}",
                    ]
                    if member.username:
                        notification_lines.append(f"📛 用户名: @{member.username}")
                    notification_lines.extend([
                        f"📊 置信度: {username_result['confidence']:.0%}",
                        f"💬 理由: {username_result['reason']}"
                    ])
                    notification = await context.bot.send_message(
                        chat_id=message.chat_id,
                        text="\n".join(notification_lines)
                    )
                    
                    if context.application.job_queue:
                        context.application.job_queue.run_once(
                            delete_notification,
                            when=3,
                            data={
                                'chat_id': message.chat_id,
                                'message_id': notification.message_id
                            }
                        )
                except TelegramError as e:
                    logger.error(f"移除违规用户名用户失败: {e}")
            else:
                logger.info(
                    f"✅ 用户名审核通过 - 用户: {display_name} (ID: {member.id}), "
                    f"用户名: @{telegram_username or '无用户名'}, "
                    f"置信度: {username_result['confidence']:.2f}, 理由: {username_result['reason']}"
                )
        
        member_names = ", ".join(member_display_names)
        try:
            await message.delete()
            logger.info(f"已删除系统服务消息 - 新成员加入: {member_names}")
        except TelegramError as e:
            logger.debug(f"删除新成员加入消息失败: {e}")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    处理群组消息
    """
    message = update.effective_message
    
    if not message:
        logger.debug("跳过无消息内容的更新: %s", update)
        return
    
    chat = getattr(message, "chat", None)
    if not chat:
        logger.debug("跳过无法确定聊天来源的消息: %s", message)
        return
    
    # 只处理群组消息
    if chat.type not in ['group', 'supergroup']:
        return
    
    try:
        sender = message.from_user or message.sender_chat
        sender_name = (
            getattr(sender, "username", None)
            or getattr(sender, "full_name", None)
            or getattr(sender, "title", None)
            or "未知用户"
        )
        sender_id = getattr(sender, "id", "N/A")
        raw_content = (
            message.text
            or message.caption
            or getattr(message, "poll", None) and "[投票]"
            or getattr(message, "sticker", None) and "[贴纸]"
            or getattr(message, "photo", None) and "[图片]"
            or getattr(message, "video", None) and "[视频]"
            or getattr(message, "document", None) and "[文件]"
            or "[非文本消息]"
        )
        # Flatten whitespace to keep log lines compact
        normalized_content = " ".join(str(raw_content).split())
        truncated_content = (
            normalized_content[:500] + "…" if len(normalized_content) > 500 else normalized_content
        )
        logger.info(
            "📩 群消息 | 群组: %s (%s) | 用户: %s (%s) | 内容: %s",
            chat.title or chat.id,
            chat.id,
            sender_name,
            sender_id,
            truncated_content
        )

        # 调试：打印消息中的链接预览和外部引用信息
        if hasattr(message, 'link_preview_options') and message.link_preview_options:
            logger.debug(f"📎 链接预览选项: {message.link_preview_options}")
        if hasattr(message, 'external_reply') and message.external_reply:
            logger.debug(f"💬 外部引用: {message.external_reply}")
            ext_reply = message.external_reply
            if hasattr(ext_reply, 'chat') and ext_reply.chat:
                logger.debug(f"   - 引用聊天: {ext_reply.chat.title} (ID: {ext_reply.chat.id})")
            if hasattr(ext_reply, 'origin') and ext_reply.origin:
                logger.debug(f"   - 引用来源: {type(ext_reply.origin).__name__}")
        
        # 检测消息
        detection_result = await spam_detector.check_message(message)
        
        # 如果跳过检测，直接返回
        if detection_result["skip_reason"]:
            user = message.from_user
            logger.info(f"跳过消息 - 原因: {detection_result['skip_reason']} | 用户: {user.username or user.first_name} (ID: {user.id})")
            print(f"⏭️  跳过检测 | 用户: {user.username or user.first_name} | 原因: {detection_result['skip_reason']}")
            return
        
        # 打印所有消息的检测结果和置信度
        user = message.from_user
        result = detection_result["result"]
        parsed_message = detection_result.get("parsed_message", {})
        risk_indicators = detection_result.get("risk_indicators", {})
        
        # 在控制台打印每条消息的置信度
        print(f"\n{'='*80}")
        print(f"📨 新消息检测")
        print(f"👤 用户: {user.username or user.first_name} (ID: {user.id})")
        
        # 显示消息内容
        message_preview = message.text[:100] if message.text else (message.caption[:100] if message.caption else '[非文本消息]')
        if (message.text and len(message.text) > 100) or (message.caption and len(message.caption) > 100):
            message_preview += '...'
        print(f"💬 内容: {message_preview}")
        
        # 使用新的解析结果显示详细信息
        risk_flags = risk_indicators.get("risk_flags", [])
        
        # 显示回复信息
        reply_info = parsed_message.get("reply")
        if reply_info and reply_info.get("is_reply"):
            reply_user = reply_info.get("reply_to_user", {})
            reply_username = reply_user.get("username") or reply_user.get("full_name", "未知")
            print(f"↩️  回复: @{reply_username} 的消息")
            reply_text = reply_info.get("reply_to_text", "")
            if reply_text:
                preview = reply_text[:50] + "..." if len(reply_text) > 50 else reply_text
                print(f"   回复内容: {preview}")
        
        # 显示频道转发信息（高风险标识）
        forward_info = parsed_message.get("forward")
        if forward_info and forward_info.get("is_forwarded"):
            forward_chat = forward_info.get("forward_from_chat")
            if forward_chat:
                channel_type = "频道" if forward_chat.get("type") == "channel" else "群组"
                channel_username = f"@{forward_chat.get('username')}" if forward_chat.get("username") else "无用户名"
                print(f"⚠️  【高风险】转发自{channel_type}: {forward_chat.get('title', '未知')} ({channel_username})")
            else:
                forward_user = forward_info.get("forward_from")
                if forward_user:
                    print(f"↪️  转发自用户: {forward_user.get('full_name', '未知')}")
        
        # 显示链接信息
        categorized_links = parsed_message.get("categorized_links", {})
        telegram_links = categorized_links.get("telegram_links", [])
        external_links = categorized_links.get("external_links", [])
        mentions = categorized_links.get("mentions", [])
        hashtags = categorized_links.get("hashtags", [])
        
        # 显示 Telegram 频道链接（高风险）
        if telegram_links:
            print(f"⚠️  【高风险】包含 Telegram 频道/群组链接: {', '.join(telegram_links[:3])}{'...' if len(telegram_links) > 3 else ''}")
        
        # 显示其他链接
        if external_links:
            print(f"🔗 包含外部链接: {', '.join(external_links[:3])}{'...' if len(external_links) > 3 else ''}")
        
        # 显示提及和标签
        if mentions:
            print(f"👥 提及用户: {', '.join(mentions[:5])}{'...' if len(mentions) > 5 else ''}")
        
        if hashtags:
            print(f"#️⃣ 话题标签: {', '.join(hashtags[:5])}{'...' if len(hashtags) > 5 else ''}")
        
        # 显示媒体类型
        media_info = parsed_message.get("media", {})
        if media_info.get("has_media"):
            media_types_cn = {
                "photo": "图片", "video": "视频", "document": "文件",
                "audio": "音频", "voice": "语音", "sticker": "贴纸",
                "video_note": "视频消息", "animation": "动画",
                "contact": "联系人", "location": "位置", "venue": "场馆",
                "poll": "投票", "dice": "骰子"
            }
            media_types = [media_types_cn.get(mt, mt) for mt in media_info.get("media_types", [])]
            print(f"📎 媒体类型: {', '.join(media_types)}")
        
        # 显示按钮信息
        buttons = parsed_message.get("buttons")
        if buttons:
            button_count = sum(len(row) for row in buttons)
            print(f"🔘 包含按钮: {button_count}个")
        
        # 显示媒体组信息
        media_group = parsed_message.get("media_group")
        if media_group and media_group.get("is_media_group"):
            print(f"� 媒体组: 相册或媒体集合")
        
        # 显示风险评估
        if risk_flags:
            print(f"\n🚨 风险标识: {' + '.join(risk_flags)}")
            print(f"⚠️  风险分数: {risk_indicators.get('risk_score', 0):.2f}")
            print(f"⚠️  风险说明: 消息包含{len(risk_flags)}个风险因素，需要重点关注！")
        
        print(f"\n🎯 垃圾消息判定: {'是 ❌' if result['is_spam'] else '否 ✅'}")
        print(f"📊 置信度: {result['confidence']:.2%} ({result['confidence']:.4f})")
        print(f"📋 类型: {result.get('category', '未知')}")
        print(f"💡 理由: {result['reason']}")
        print(f"🔧 处理: {'删除+封禁' if detection_result['should_delete'] else '保留'}")
        print(f"{'='*80}\n")
        
        # 如果需要删除消息和封禁用户
        if detection_result["should_delete"] and detection_result["should_ban"]:
            logger.warning(
                f"检测到垃圾消息 - 用户: {user.username or user.first_name} (ID: {user.id}), "
                f"置信度: {result['confidence']:.2f}, "
                f"类型: {result.get('category', 'unknown')}, "
                f"理由: {result['reason']}"
            )
            
            try:
                # 封禁用户（先封禁再删除消息，这样可以捕获封禁产生的系统消息）
                await context.bot.ban_chat_member(
                    chat_id=message.chat_id,
                    user_id=user.id
                )
                chat = message.chat
                logger.info(
                    "已封禁用户 - 群组: %s (%s) - %s (ID: %s)",
                    chat.title or chat.id,
                    chat.id,
                    user.username or user.first_name,
                    user.id
                )

                log_ban_event(
                    category=result.get("category") or "message_violation",
                    chat=chat,
                    user=user,
                    reason=result["reason"],
                    confidence=result["confidence"],
                    extra={
                        "trigger": "message",
                        "message_id": message.message_id,
                        "risk_flags": risk_indicators.get("risk_flags", []),
                        "risk_score": risk_indicators.get("risk_score"),
                    },
                )
                
                # 删除垃圾消息
                await message.delete()
                logger.info(f"已删除消息 - 消息 ID: {message.message_id}")
                
                # 发送通知消息（可选）
                notification_text = (
                    f"⚠️ 检测到垃圾消息并已处理\n"
                    f"👤 用户: {user.username or user.first_name}\n"
                    f"📋 类型: {result.get('category', '未知')}\n"
                    f"📊 置信度: {result['confidence']:.0%}\n"
                    f"💬 理由: {result['reason']}"
                )
                
                # 发送通知并在 3 秒后自动删除
                notification = await context.bot.send_message(
                    chat_id=message.chat_id,
                    text=notification_text
                )
                
                # 3 秒后删除通知消息（如果 JobQueue 可用）
                if context.application.job_queue:
                    context.application.job_queue.run_once(
                        delete_notification,
                        when=3,
                        data={
                            'chat_id': message.chat_id,
                            'message_id': notification.message_id
                        }
                    )
                else:
                    logger.warning("JobQueue 未配置，通知消息将不会自动删除")
                
            except TelegramError as e:
                logger.error(f"处理垃圾消息时出错: {e}")
                
                # 检查是否是权限问题
                if "not enough rights" in str(e).lower():
                    logger.error("机器人没有足够的权限！请确保机器人是群组管理员。")
                elif "message to delete not found" in str(e).lower():
                    logger.warning("消息已被删除或不存在")
        
        else:
            # 正常消息，记录日志
            logger.info(
                f"✅ 正常消息 - 用户: {user.username or user.first_name} (ID: {user.id}), "
                f"置信度: {result['confidence']:.2f} (低于阈值 {config.CONFIDENCE_THRESHOLD})"
            )
    
    except Exception as e:
        logger.error(f"处理消息时发生未预期的错误: {e}", exc_info=True)


async def delete_notification(context: ContextTypes.DEFAULT_TYPE):
    """删除通知消息的回调函数"""
    job_data = context.job.data
    try:
        await context.bot.delete_message(
            chat_id=job_data['chat_id'],
            message_id=job_data['message_id']
        )
        logger.debug("已删除通知消息")
    except TelegramError as e:
        logger.warning(f"删除通知消息失败: {e}")


def _format_ban_report(stats: Dict[str, Any]) -> Optional[str]:
    """根据封禁统计构建报告文本。"""
    total = stats.get("total", 0)
    unique_accounts = stats.get("unique_accounts", 0)
    stats_by_chat = stats.get("by_chat", {})
    since = stats.get("since")
    until = stats.get("until")

    if not total:
        return None

    if not since or not until:
        logger.warning("封禁统计缺少时间范围信息，无法构建报告")
        return None

    header_lines = [
        "📊 垃圾账号封禁统计",
        f"🕘 统计范围: {since.strftime('%Y-%m-%d %H:%M')} - {until.strftime('%Y-%m-%d %H:%M')} (北京时间)",
        f"🚫 封禁记录: {total} 条",
        f"👤 唯一账号: {unique_accounts} 个",
    ]

    category_summary_blocks = []
    category_stats = stats.get("by_category") or {}
    if category_stats:
        sorted_categories = sorted(
            category_stats.items(),
            key=lambda item: item[1].get("total", 0),
            reverse=True
        )
        summary_lines = ["📌 封禁原因统计:"]
        for category, cat_stats in sorted_categories:
            label = describe_ban_category(category)
            summary_lines.append(
                f"- {label}: {cat_stats.get('total', 0)} 条，"
                f"{cat_stats.get('unique_accounts', 0)} 个账号"
            )
        category_summary_blocks.append("\n".join(summary_lines))

    report_parts = ["\n".join(header_lines)]
    report_parts.extend(category_summary_blocks)
    return "\n\n".join(report_parts)


async def send_daily_ban_report(context: ContextTypes.DEFAULT_TYPE):
    """每日封禁统计报告，发送给管理员用户并保留消息。"""
    stats = get_recent_ban_stats(window_hours=24)
    report_text = _format_ban_report(stats)

    if not report_text:
        logger.debug("最近 24 小时没有封禁记录，跳过封禁统计报告发送")
        return

    target_user_ids = sorted(set(config.ADMIN_USER_IDS))
    if not target_user_ids:
        logger.warning("未配置管理员用户 ID，封禁统计报告无法发送")
        return

    for user_id in target_user_ids:
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=report_text
            )
        except TelegramError as exc:
            logger.error(f"发送封禁统计报告失败 (user_id={user_id}): {exc}")


async def ban_report_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """命令触发的封禁统计报告。"""
    message = update.effective_message
    user = update.effective_user

    if not message:
        logger.debug("封禁统计命令缺少消息内容: %s", update)
        return

    user_id = getattr(user, "id", None)
    if user_id not in config.ADMIN_USER_IDS:
        await message.reply_text("❌ 您没有权限执行此命令。")
        return

    stats = get_recent_ban_stats(window_hours=24)
    report_text = _format_ban_report(stats)

    if not report_text:
        await message.reply_text("✅ 最近 24 小时未封禁新的垃圾账号。")
        return

    await message.reply_text(report_text)


async def log_stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """统计日志中的封禁账号数量和垃圾消息数量。"""
    message = update.effective_message
    user = update.effective_user

    if not message:
        logger.debug("日志统计命令缺少消息内容: %s", update)
        return

    user_id = getattr(user, "id", None)
    if user_id not in config.ADMIN_USER_IDS:
        await message.reply_text("❌ 您没有权限执行此命令。")
        return

    stats = get_total_log_stats()
    log_path = stats.get("log_path")

    if not stats.get("log_exists"):
        await message.reply_text(f"⚠️ 未找到日志文件: {log_path}")
        return

    def format_time(value: Optional[datetime]) -> str:
        if not value:
            return "无记录"
        try:
            return value.astimezone(BEIJING_TZ).strftime("%Y-%m-%d %H:%M")
        except Exception:
            return value.strftime("%Y-%m-%d %H:%M")

    ban_range = "无记录"
    if stats.get("total_ban_events", 0):
        ban_range = f"{format_time(stats.get('earliest_ban_time'))} ~ {format_time(stats.get('latest_ban_time'))}"

    spam_range = "无记录"
    if stats.get("total_spam_messages", 0):
        spam_range = f"{format_time(stats.get('earliest_spam_time'))} ~ {format_time(stats.get('latest_spam_time'))}"

    reply_text = (
        "📊 **日志统计概览**\n"
        f"🗂️ 日志文件: `{log_path}`\n"
        f"🚫 封禁记录: {stats.get('total_ban_events', 0)} 条（唯一账号 {stats.get('unique_banned_accounts', 0)} 个）\n"
        f"🚨 垃圾消息: {stats.get('total_spam_messages', 0)} 条\n"
        f"🕰️ 封禁时间范围: {ban_range}\n"
        f"🕰️ 垃圾消息时间范围: {spam_range}"
    )

    await message.reply_text(reply_text, parse_mode="Markdown")


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理错误"""
    logger.error(f"更新 {update} 导致错误: {context.error}", exc_info=context.error)


def main():
    """主函数"""
    try:
        # 验证配置
        config.validate_config()
        
        logger.info("正在启动 Telegram 垃圾消息过滤机器人...")
        
        # 创建应用构建器
        app_builder = (
            Application.builder()
            .token(config.TELEGRAM_BOT_TOKEN)
            .post_init(setup_bot_commands)
        )
        
        # 如果配置了代理，则使用代理
        if config.PROXY_URL:
            logger.info(f"🌐 使用代理: {config.PROXY_URL}")
            from telegram.request import HTTPXRequest
            request = HTTPXRequest(
                connection_pool_size=8,
                proxy_url=config.PROXY_URL
            )
            app_builder.request(request)
        
        # 构建应用
        application = app_builder.build()
        
        # 添加命令处理器
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("status", status_command))
        application.add_handler(CommandHandler(["banstats", "banreport"], ban_report_command))
        application.add_handler(CommandHandler("logstats", log_stats_command))
        
        # 添加系统服务消息处理器（优先级最高，处理用户离开/加入的系统消息）
        application.add_handler(
            MessageHandler(
                filters.StatusUpdate.LEFT_CHAT_MEMBER | filters.StatusUpdate.NEW_CHAT_MEMBERS,
                handle_service_message
            ),
            group=-1  # 使用负数组让它优先处理
        )
        
        # 添加消息处理器（处理所有文本消息和媒体消息）
        application.add_handler(
            MessageHandler(
                filters.ALL & ~filters.COMMAND & ~filters.StatusUpdate.LEFT_CHAT_MEMBER & ~filters.StatusUpdate.NEW_CHAT_MEMBERS,
                handle_message
            )
        )
        
        # 添加错误处理器
        application.add_error_handler(error_handler)

        # 安排每日封禁统计任务
        if application.job_queue:
            report_time = time(hour=23, minute=0, tzinfo=BEIJING_TZ)
            application.job_queue.run_daily(
                send_daily_ban_report,
                time=report_time,
                name="daily_ban_report"
            )
        else:
            logger.warning("JobQueue 未配置，封禁统计报告任务无法安排")
        
        # 启动机器人
        logger.info("✅ 机器人启动成功！正在监听消息...")
        logger.info(f"📡 使用模型: {config.LLM_MODEL}")
        logger.info(f"🎯 置信度阈值: {config.CONFIDENCE_THRESHOLD}")
        
        # 开始轮询
        application.run_polling(allowed_updates=Update.ALL_TYPES)
        
    except ValueError as e:
        logger.error(f"❌ 配置错误: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ 启动失败: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
