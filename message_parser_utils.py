"""
Telegram 消息解析工具模块
提供各种消息组件的解析和格式化功能
"""
from typing import Dict, List, Optional, Any
from telegram import Message, User, Chat, MessageEntity, PhotoSize
import logging

logger = logging.getLogger(__name__)


def format_user_info(user: Optional[User]) -> Dict[str, Any]:
    """
    格式化用户信息
    
    Args:
        user: Telegram User 对象
    
    Returns:
        用户信息字典
    """
    if not user:
        return {
            "id": None,
            "username": None,
            "full_name": "未知用户",
            "is_bot": False,
            "first_name": None,
            "last_name": None,
            "language_code": None
        }
    
    return {
        "id": user.id,
        "username": user.username,
        "full_name": f"{user.first_name} {user.last_name or ''}".strip(),
        "is_bot": user.is_bot,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "language_code": user.language_code
    }


def format_chat_info(chat: Optional[Chat]) -> Dict[str, Any]:
    """
    格式化频道/群组信息
    
    Args:
        chat: Telegram Chat 对象
    
    Returns:
        频道/群组信息字典
    """
    if not chat:
        return {
            "id": None,
            "type": None,
            "title": None,
            "username": None,
            "description": None
        }
    
    return {
        "id": chat.id,
        "type": chat.type,
        "title": chat.title,
        "username": chat.username,
        "description": getattr(chat, "description", None)  # 使用 getattr 安全获取，避免属性错误
    }


def extract_entities(message: Message) -> List[Dict[str, Any]]:
    """
    提取消息中的所有实体（链接、提及、标签等）
    
    Args:
        message: Telegram 消息对象
    
    Returns:
        实体信息列表
    """
    entities_list = []
    
    # 处理消息文本实体
    if message.entities and message.text:
        for entity in message.entities:
            entity_info = _parse_entity(entity, message.text)
            if entity_info:
                entities_list.append(entity_info)
    
    # 处理图片说明实体
    if message.caption_entities and message.caption:
        for entity in message.caption_entities:
            entity_info = _parse_entity(entity, message.caption)
            if entity_info:
                entities_list.append(entity_info)
    
    return entities_list


def _parse_entity(entity: MessageEntity, text: str) -> Optional[Dict[str, Any]]:
    """
    解析单个消息实体
    
    Args:
        entity: MessageEntity 对象
        text: 消息文本
    
    Returns:
        实体信息字典
    """
    entity_text = text[entity.offset:entity.offset + entity.length]
    
    entity_info = {
        "type": entity.type,
        "text": entity_text,
        "offset": entity.offset,
        "length": entity.length
    }
    
    # 根据实体类型添加额外信息
    if entity.type == "text_link":
        entity_info["url"] = entity.url
    elif entity.type == "text_mention":
        entity_info["user"] = format_user_info(entity.user)
    
    return entity_info


def extract_media_info(message: Message) -> Dict[str, Any]:
    """
    提取消息中的媒体信息
    
    Args:
        message: Telegram 消息对象
    
    Returns:
        媒体信息字典
    """
    media_info = {
        "has_media": False,
        "media_types": [],
        "details": {}
    }
    
    # 图片
    if message.photo:
        media_info["has_media"] = True
        media_info["media_types"].append("photo")
        # 获取最大尺寸的图片
        largest_photo = max(message.photo, key=lambda p: p.file_size or 0)
        media_info["details"]["photo"] = {
            "file_id": largest_photo.file_id,
            "file_unique_id": largest_photo.file_unique_id,
            "width": largest_photo.width,
            "height": largest_photo.height,
            "file_size": largest_photo.file_size
        }
    
    # 视频
    if message.video:
        media_info["has_media"] = True
        media_info["media_types"].append("video")
        media_info["details"]["video"] = {
            "file_id": message.video.file_id,
            "file_unique_id": message.video.file_unique_id,
            "width": message.video.width,
            "height": message.video.height,
            "duration": message.video.duration,
            "file_size": message.video.file_size,
            "mime_type": message.video.mime_type
        }
    
    # 文档
    if message.document:
        media_info["has_media"] = True
        media_info["media_types"].append("document")
        media_info["details"]["document"] = {
            "file_id": message.document.file_id,
            "file_unique_id": message.document.file_unique_id,
            "file_name": message.document.file_name,
            "mime_type": message.document.mime_type,
            "file_size": message.document.file_size
        }
    
    # 音频
    if message.audio:
        media_info["has_media"] = True
        media_info["media_types"].append("audio")
        media_info["details"]["audio"] = {
            "file_id": message.audio.file_id,
            "file_unique_id": message.audio.file_unique_id,
            "duration": message.audio.duration,
            "performer": message.audio.performer,
            "title": message.audio.title,
            "mime_type": message.audio.mime_type,
            "file_size": message.audio.file_size
        }
    
    # 语音
    if message.voice:
        media_info["has_media"] = True
        media_info["media_types"].append("voice")
        media_info["details"]["voice"] = {
            "file_id": message.voice.file_id,
            "file_unique_id": message.voice.file_unique_id,
            "duration": message.voice.duration,
            "mime_type": message.voice.mime_type,
            "file_size": message.voice.file_size
        }
    
    # 视频消息（圆形视频）
    if message.video_note:
        media_info["has_media"] = True
        media_info["media_types"].append("video_note")
        media_info["details"]["video_note"] = {
            "file_id": message.video_note.file_id,
            "file_unique_id": message.video_note.file_unique_id,
            "length": message.video_note.length,
            "duration": message.video_note.duration,
            "file_size": message.video_note.file_size
        }
    
    # 贴纸
    if message.sticker:
        media_info["has_media"] = True
        media_info["media_types"].append("sticker")
        media_info["details"]["sticker"] = {
            "file_id": message.sticker.file_id,
            "file_unique_id": message.sticker.file_unique_id,
            "width": message.sticker.width,
            "height": message.sticker.height,
            "is_animated": message.sticker.is_animated,
            "is_video": message.sticker.is_video,
            "emoji": message.sticker.emoji,
            "set_name": message.sticker.set_name,
            "file_size": message.sticker.file_size
        }
    
    # 动画 GIF
    if message.animation:
        media_info["has_media"] = True
        media_info["media_types"].append("animation")
        media_info["details"]["animation"] = {
            "file_id": message.animation.file_id,
            "file_unique_id": message.animation.file_unique_id,
            "width": message.animation.width,
            "height": message.animation.height,
            "duration": message.animation.duration,
            "file_name": message.animation.file_name,
            "mime_type": message.animation.mime_type,
            "file_size": message.animation.file_size
        }
    
    # 联系人
    if message.contact:
        media_info["has_media"] = True
        media_info["media_types"].append("contact")
        media_info["details"]["contact"] = {
            "phone_number": message.contact.phone_number,
            "first_name": message.contact.first_name,
            "last_name": message.contact.last_name,
            "user_id": message.contact.user_id,
            "vcard": message.contact.vcard
        }
    
    # 位置
    if message.location:
        media_info["has_media"] = True
        media_info["media_types"].append("location")
        media_info["details"]["location"] = {
            "latitude": message.location.latitude,
            "longitude": message.location.longitude,
            "horizontal_accuracy": message.location.horizontal_accuracy,
            "live_period": message.location.live_period,
            "heading": message.location.heading,
            "proximity_alert_radius": message.location.proximity_alert_radius
        }
    
    # 场馆
    if message.venue:
        media_info["has_media"] = True
        media_info["media_types"].append("venue")
        media_info["details"]["venue"] = {
            "location": {
                "latitude": message.venue.location.latitude,
                "longitude": message.venue.location.longitude
            },
            "title": message.venue.title,
            "address": message.venue.address,
            "foursquare_id": message.venue.foursquare_id,
            "foursquare_type": message.venue.foursquare_type
        }
    
    # 投票
    if message.poll:
        media_info["has_media"] = True
        media_info["media_types"].append("poll")
        media_info["details"]["poll"] = {
            "id": message.poll.id,
            "question": message.poll.question,
            "options": [{"text": opt.text, "voter_count": opt.voter_count} for opt in message.poll.options],
            "total_voter_count": message.poll.total_voter_count,
            "is_closed": message.poll.is_closed,
            "is_anonymous": message.poll.is_anonymous,
            "type": message.poll.type,
            "allows_multiple_answers": message.poll.allows_multiple_answers
        }
    
    # 骰子
    if message.dice:
        media_info["has_media"] = True
        media_info["media_types"].append("dice")
        media_info["details"]["dice"] = {
            "emoji": message.dice.emoji,
            "value": message.dice.value
        }
    
    return media_info


def extract_forward_info(message: Message) -> Optional[Dict[str, Any]]:
    """
    提取转发消息信息
    
    Args:
        message: Telegram 消息对象
    
    Returns:
        转发信息字典，如果不是转发消息则返回 None
    """
    forward_info = {
        "is_forwarded": False,
        "forward_from": None,
        "forward_from_chat": None,
        "forward_from_message_id": None,
        "forward_signature": None,
        "forward_sender_name": None,
        "forward_date": None,
        "forward_origin": None
    }
    
    # 安全地获取转发相关属性
    forward_date = getattr(message, 'forward_date', None)
    forward_from = getattr(message, 'forward_from', None)
    forward_from_chat = getattr(message, 'forward_from_chat', None)
    forward_origin = getattr(message, 'forward_origin', None)
    
    # 检查是否是转发消息
    if not (forward_date or forward_from or forward_from_chat or forward_origin):
        return None
    
    forward_info["is_forwarded"] = True
    forward_info["forward_date"] = forward_date
    forward_info["forward_from_message_id"] = getattr(message, 'forward_from_message_id', None)
    forward_info["forward_signature"] = getattr(message, 'forward_signature', None)
    forward_info["forward_sender_name"] = getattr(message, 'forward_sender_name', None)
    forward_info["forward_origin"] = forward_origin
    
    # 转发自用户
    if forward_from:
        forward_info["forward_from"] = format_user_info(forward_from)
    
    # 转发自频道/群组
    if forward_from_chat:
        forward_info["forward_from_chat"] = format_chat_info(forward_from_chat)
    
    # 处理新版本的 forward_origin（如果存在）
    if forward_origin:
        try:
            # forward_origin 可能是 MessageOriginUser, MessageOriginChat, MessageOriginChannel 等
            origin_type = type(forward_origin).__name__
            if hasattr(forward_origin, 'sender_user'):
                forward_info["forward_from"] = format_user_info(forward_origin.sender_user)
            elif hasattr(forward_origin, 'sender_chat'):
                forward_info["forward_from_chat"] = format_chat_info(forward_origin.sender_chat)
            elif hasattr(forward_origin, 'chat'):
                forward_info["forward_from_chat"] = format_chat_info(forward_origin.chat)
        except Exception as e:
            logger.warning(f"处理 forward_origin 时出错: {e}")
    
    return forward_info


def extract_reply_info(message: Message) -> Optional[Dict[str, Any]]:
    """
    提取回复消息信息（增强版，提取更多被回复消息的详细信息）
    
    Args:
        message: Telegram 消息对象
    
    Returns:
        回复信息字典，如果不是回复消息则返回 None
    """
    if not message.reply_to_message:
        return None
    
    replied_msg = message.reply_to_message
    
    reply_info = {
        "is_reply": True,
        "reply_to_message_id": replied_msg.message_id,
        "reply_to_user": format_user_info(replied_msg.from_user),
        "reply_to_text": replied_msg.text or replied_msg.caption,
        "reply_to_date": replied_msg.date,
        "reply_to_has_media": bool(
            replied_msg.photo or replied_msg.video or replied_msg.document or
            replied_msg.audio or replied_msg.voice or replied_msg.sticker
        )
    }
    
    # 提取被回复消息的实体（链接、提及等）
    reply_info["reply_to_entities"] = extract_entities(replied_msg)
    
    # 提取被回复消息的媒体信息
    reply_info["reply_to_media"] = extract_media_info(replied_msg)
    
    # 如果回复的消息也是转发消息（安全检查）
    forward_date = getattr(replied_msg, 'forward_date', None)
    forward_origin = getattr(replied_msg, 'forward_origin', None)
    if forward_date or forward_origin:
        reply_info["reply_to_is_forwarded"] = True
        reply_info["reply_to_forward_info"] = extract_forward_info(replied_msg)
    
    # 提取被回复消息的按钮信息
    reply_info["reply_to_buttons"] = extract_buttons_info(replied_msg)
    
    return reply_info


def extract_buttons_info(message: Message) -> Optional[List[List[Dict[str, Any]]]]:
    """
    提取消息中的按钮信息（Inline Keyboard）
    
    Args:
        message: Telegram 消息对象
    
    Returns:
        按钮信息列表（二维数组），如果没有按钮则返回 None
    """
    if not message.reply_markup or not hasattr(message.reply_markup, 'inline_keyboard'):
        return None
    
    buttons = []
    for row in message.reply_markup.inline_keyboard:
        button_row = []
        for button in row:
            button_info = {
                "text": button.text,
                "url": button.url,
                "callback_data": button.callback_data,
                "switch_inline_query": button.switch_inline_query,
                "switch_inline_query_current_chat": button.switch_inline_query_current_chat
            }
            button_row.append(button_info)
        buttons.append(button_row)
    
    return buttons if buttons else None


def extract_media_group_info(message: Message) -> Optional[Dict[str, Any]]:
    """
    提取媒体组信息（相册）
    
    Args:
        message: Telegram 消息对象
    
    Returns:
        媒体组信息字典，如果不是媒体组则返回 None
    """
    if not message.media_group_id:
        return None
    
    return {
        "media_group_id": message.media_group_id,
        "is_media_group": True
    }


def extract_urls_from_text(text: str) -> List[str]:
    """
    从文本中提取所有 URL（使用简单的正则匹配）
    
    Args:
        text: 文本内容
    
    Returns:
        URL 列表
    """
    import re
    url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
    return re.findall(url_pattern, text)


def categorize_links(entities: List[Dict[str, Any]]) -> Dict[str, List[str]]:
    """
    对链接进行分类
    
    Args:
        entities: 实体列表
    
    Returns:
        分类后的链接字典
    """
    categorized = {
        "telegram_links": [],
        "external_links": [],
        "mentions": [],
        "hashtags": [],
        "bot_commands": []
    }
    
    for entity in entities:
        if entity["type"] in ["url", "text_link"]:
            url = entity.get("url") or entity.get("text", "")
            if "t.me/" in url.lower() or "telegram.me/" in url.lower():
                categorized["telegram_links"].append(url)
            else:
                categorized["external_links"].append(url)
        elif entity["type"] == "mention":
            categorized["mentions"].append(entity["text"])
        elif entity["type"] == "hashtag":
            categorized["hashtags"].append(entity["text"])
        elif entity["type"] == "bot_command":
            categorized["bot_commands"].append(entity["text"])
    
    return categorized
