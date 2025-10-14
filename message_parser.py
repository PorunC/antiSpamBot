"""
Telegram 消息解析模块
提供完整的消息解析功能，提取所有可能的消息信息
"""
import logging
from typing import Dict, Any, Optional
from telegram import Message
from message_parser_utils import (
    format_user_info,
    format_chat_info,
    extract_entities,
    extract_media_info,
    extract_forward_info,
    extract_reply_info,
    extract_buttons_info,
    extract_media_group_info,
    categorize_links
)

logger = logging.getLogger(__name__)


class MessageParser:
    """Telegram 消息解析器"""
    
    def __init__(self):
        """初始化解析器"""
        logger.info("消息解析器初始化完成")
    
    def parse_message(self, message: Message) -> Dict[str, Any]:
        """
        完整解析 Telegram 消息
        
        Args:
            message: Telegram 消息对象
        
        Returns:
            包含所有解析信息的字典
        """
        try:
            parsed_data = {
                # 基本信息
                "message_id": message.message_id,
                "date": message.date,
                "chat": format_chat_info(message.chat),
                "from_user": format_user_info(message.from_user),
                
                # 文本内容
                "text": message.text,
                "caption": message.caption,
                
                # 实体信息（链接、提及、标签等）
                "entities": extract_entities(message),
                
                # 媒体信息
                "media": extract_media_info(message),
                
                # 转发信息
                "forward": extract_forward_info(message),
                
                # 回复信息
                "reply": extract_reply_info(message),
                
                # 按钮信息
                "buttons": extract_buttons_info(message),
                
                # 媒体组信息
                "media_group": extract_media_group_info(message),
                
                # 其他标记
                "is_automatic_forward": message.is_automatic_forward,
                "has_protected_content": message.has_protected_content,
                "edit_date": message.edit_date,
                "author_signature": message.author_signature,
                
                # 特殊消息类型
                "is_topic_message": message.is_topic_message,
                "message_thread_id": message.message_thread_id,
            }
            
            # 链接分类
            if parsed_data["entities"]:
                parsed_data["categorized_links"] = categorize_links(parsed_data["entities"])
            else:
                parsed_data["categorized_links"] = {
                    "telegram_links": [],
                    "external_links": [],
                    "mentions": [],
                    "hashtags": [],
                    "bot_commands": []
                }
            
            logger.debug(f"消息解析完成 - ID: {message.message_id}")
            return parsed_data
            
        except Exception as e:
            logger.error(f"消息解析失败: {e}", exc_info=True)
            return self._get_minimal_parsed_data(message)
    
    def format_for_analysis(
        self, 
        parsed_message: Dict[str, Any],
        whitelist_user_ids: set = None
    ) -> str:
        """
        将解析后的消息格式化为适合 LLM 分析的文本
        
        Args:
            parsed_message: 解析后的消息字典
            whitelist_user_ids: 白名单用户ID集合（管理员+系统白名单）
        
        Returns:
            格式化的文本字符串
        """
        if whitelist_user_ids is None:
            whitelist_user_ids = set()
        
        parts = []
        
        # 基本文本内容
        if parsed_message.get("text"):
            parts.append(f"【消息文本】\n{parsed_message['text']}")
        
        if parsed_message.get("caption"):
            parts.append(f"【媒体说明】\n{parsed_message['caption']}")
        
        # 转发信息（高风险标识）
        forward_info = parsed_message.get("forward")
        if forward_info and forward_info.get("is_forwarded"):
            forward_parts = ["【⚠️ 转发消息】"]
            
            if forward_info.get("forward_from_chat"):
                chat_info = forward_info["forward_from_chat"]
                chat_type = "频道" if chat_info.get("type") == "channel" else "群组"
                chat_name = chat_info.get("title", "未知")
                chat_username = f"@{chat_info['username']}" if chat_info.get("username") else "无用户名"
                forward_parts.append(f"转发自{chat_type}: {chat_name} ({chat_username})")
            elif forward_info.get("forward_from"):
                user_info = forward_info["forward_from"]
                forward_parts.append(f"转发自用户: {user_info.get('full_name')} (@{user_info.get('username') or '无'})")
            elif forward_info.get("forward_sender_name"):
                forward_parts.append(f"转发自: {forward_info['forward_sender_name']}")
            
            if forward_info.get("forward_signature"):
                forward_parts.append(f"签名: {forward_info['forward_signature']}")
            
            parts.append("\n".join(forward_parts))
        
        # 回复信息（增强版：包含被回复消息的完整上下文）
        reply_info = parsed_message.get("reply")
        if reply_info and reply_info.get("is_reply"):
            reply_user = reply_info.get("reply_to_user", {})
            reply_user_id = reply_user.get("id")
            is_replying_to_whitelist = reply_user_id in whitelist_user_ids if reply_user_id else False
            
            if is_replying_to_whitelist:
                # 回复白名单用户：完全不显示被回复消息的内容，只分析用户自己的回复
                reply_parts = ["【回复消息】"]
                reply_parts.append(f"用户正在回复白名单用户（管理员/系统账号）: {reply_user.get('full_name', '未知')}")
                reply_parts.append("🔴 重要：被回复用户是白名单用户，请**仅根据当前用户的回复内容本身**判断，完全忽略被回复消息的内容")
                reply_parts.append("✅ 正常的聊天回复（如打招呼、表情、礼貌用语等）不应被判定为垃圾消息")
                # 不显示被回复消息的内容，避免影响判断
            else:
                # 回复普通用户：显示完整上下文分析
                reply_parts = ["【回复消息 - 上下文分析】"]
                reply_parts.append(f"被回复的用户: {reply_user.get('full_name', '未知')} (@{reply_user.get('username') or '无'})")
                
                # 被回复消息的文本内容
                if reply_info.get("reply_to_text"):
                    reply_text = reply_info["reply_to_text"]
                    if len(reply_text) > 300:
                        reply_text = reply_text[:300] + "..."
                    reply_parts.append(f"被回复的消息内容:\n{reply_text}")
                
                # 被回复消息是否为转发
                if reply_info.get("reply_to_is_forwarded"):
                    forward_info = reply_info.get("reply_to_forward_info", {})
                    if forward_info and forward_info.get("forward_from_chat"):
                        chat_info = forward_info["forward_from_chat"]
                        chat_type = "频道" if chat_info.get("type") == "channel" else "群组"
                        chat_name = chat_info.get("title", "未知")
                        reply_parts.append(f"(被回复的消息是转发自{chat_type}: {chat_name})")
                
                # 被回复消息中的链接
                reply_entities = reply_info.get("reply_to_entities", [])
                if reply_entities:
                    reply_links = categorize_links(reply_entities)
                    if reply_links.get("telegram_links"):
                        reply_parts.append(f"(被回复消息包含 Telegram 链接: {', '.join(reply_links['telegram_links'][:2])})")
                    if reply_links.get("external_links"):
                        reply_parts.append(f"(被回复消息包含外部链接: {', '.join(reply_links['external_links'][:2])})")
                    if reply_links.get("mentions"):
                        reply_parts.append(f"(被回复消息提及: {', '.join(reply_links['mentions'][:3])})")
                
                # 被回复消息中的媒体
                reply_media = reply_info.get("reply_to_media", {})
                if reply_media.get("has_media"):
                    media_types_cn = {
                        "photo": "图片", "video": "视频", "document": "文件",
                        "audio": "音频", "voice": "语音", "sticker": "贴纸",
                        "contact": "联系人", "location": "位置"
                    }
                    media_types = [media_types_cn.get(mt, mt) for mt in reply_media.get("media_types", [])]
                    reply_parts.append(f"(被回复消息包含: {', '.join(media_types)})")
                
                # 被回复消息中的按钮
                reply_buttons = reply_info.get("reply_to_buttons")
                if reply_buttons:
                    button_count = sum(len(row) for row in reply_buttons)
                    reply_parts.append(f"(被回复消息包含 {button_count} 个按钮)")
            
            parts.append("\n".join(reply_parts))
        
        # 链接信息（重点关注）
        categorized_links = parsed_message.get("categorized_links", {})
        
        # Telegram 链接（高风险）
        telegram_links = categorized_links.get("telegram_links", [])
        if telegram_links:
            parts.append(f"【⚠️ Telegram 频道/群组链接】\n" + "\n".join(f"- {link}" for link in telegram_links))
        
        # 外部链接
        external_links = categorized_links.get("external_links", [])
        if external_links:
            parts.append(f"【外部链接】\n" + "\n".join(f"- {link}" for link in external_links))
        
        # 提及
        mentions = categorized_links.get("mentions", [])
        if mentions:
            parts.append(f"【提及用户】\n" + ", ".join(mentions))
        
        # 标签
        hashtags = categorized_links.get("hashtags", [])
        if hashtags:
            parts.append(f"【话题标签】\n" + ", ".join(hashtags))
        
        # 媒体信息
        media_info = parsed_message.get("media", {})
        if media_info.get("has_media"):
            media_types = ", ".join(media_info.get("media_types", []))
            parts.append(f"【媒体类型】\n{media_types}")
            
            # 联系人信息（高风险）
            if "contact" in media_info.get("media_types", []):
                contact = media_info["details"].get("contact", {})
                parts.append(
                    f"【⚠️ 联系人信息】\n"
                    f"姓名: {contact.get('first_name', '')} {contact.get('last_name', '')}\n"
                    f"电话: {contact.get('phone_number', '未知')}"
                )
            
            # 位置信息
            if "location" in media_info.get("media_types", []):
                location = media_info["details"].get("location", {})
                parts.append(
                    f"【位置信息】\n"
                    f"纬度: {location.get('latitude', 0)}, "
                    f"经度: {location.get('longitude', 0)}"
                )
        
        # 按钮信息（常见于广告消息）
        buttons = parsed_message.get("buttons")
        if buttons:
            button_texts = []
            for row in buttons:
                for button in row:
                    btn_text = button.get("text", "")
                    btn_url = button.get("url", "")
                    if btn_url:
                        button_texts.append(f"{btn_text} -> {btn_url}")
                    else:
                        button_texts.append(btn_text)
            
            if button_texts:
                parts.append(f"【⚠️ 消息按钮】\n" + "\n".join(f"- {btn}" for btn in button_texts))
        
        # 媒体组信息
        media_group = parsed_message.get("media_group")
        if media_group and media_group.get("is_media_group"):
            parts.append("【媒体组】\n此消息属于相册或媒体组")
        
        # 其他标记
        if parsed_message.get("is_automatic_forward"):
            parts.append("【自动转发】\n此消息为频道自动转发到讨论组")
        
        if parsed_message.get("has_protected_content"):
            parts.append("【受保护内容】\n此消息内容受保护，无法转发或保存")
        
        if parsed_message.get("edit_date"):
            parts.append(f"【已编辑】\n编辑时间: {parsed_message['edit_date']}")
        
        return "\n\n".join(parts)
    
    def extract_risk_indicators(self, parsed_message: Dict[str, Any]) -> Dict[str, Any]:
        """
        从解析的消息中提取风险指标
        
        Args:
            parsed_message: 解析后的消息字典
        
        Returns:
            风险指标字典
        """
        risk_indicators = {
            "has_channel_forward": False,
            "has_telegram_links": False,
            "has_external_links": False,
            "has_contact_info": False,
            "has_buttons": False,
            "is_media_group": False,
            "has_multiple_risks": False,
            "risk_score": 0.0,
            "risk_flags": []
        }
        
        # 检查频道转发（高风险）
        forward_info = parsed_message.get("forward")
        if forward_info and forward_info.get("is_forwarded"):
            if forward_info.get("forward_from_chat"):
                risk_indicators["has_channel_forward"] = True
                risk_indicators["risk_score"] += 0.4
                risk_indicators["risk_flags"].append("频道转发")
        
        # 检查 Telegram 链接（高风险）
        telegram_links = parsed_message.get("categorized_links", {}).get("telegram_links", [])
        if telegram_links:
            risk_indicators["has_telegram_links"] = True
            risk_indicators["risk_score"] += 0.3
            risk_indicators["risk_flags"].append(f"{len(telegram_links)}个Telegram链接")
        
        # 检查外部链接
        external_links = parsed_message.get("categorized_links", {}).get("external_links", [])
        if external_links:
            risk_indicators["has_external_links"] = True
            risk_indicators["risk_score"] += 0.1 * min(len(external_links), 3)
            risk_indicators["risk_flags"].append(f"{len(external_links)}个外部链接")
        
        # 检查联系人信息（高风险）
        media_info = parsed_message.get("media", {})
        if "contact" in media_info.get("media_types", []):
            risk_indicators["has_contact_info"] = True
            risk_indicators["risk_score"] += 0.3
            risk_indicators["risk_flags"].append("包含联系人")
        
        # 检查按钮（常见于广告）
        if parsed_message.get("buttons"):
            risk_indicators["has_buttons"] = True
            risk_indicators["risk_score"] += 0.2
            risk_indicators["risk_flags"].append("包含按钮")
        
        # 检查媒体组
        if parsed_message.get("media_group"):
            risk_indicators["is_media_group"] = True
            risk_indicators["risk_score"] += 0.1
            risk_indicators["risk_flags"].append("媒体组")
        
        # 判断是否有多个风险因素
        risk_count = sum([
            risk_indicators["has_channel_forward"],
            risk_indicators["has_telegram_links"],
            risk_indicators["has_external_links"],
            risk_indicators["has_contact_info"],
            risk_indicators["has_buttons"]
        ])
        
        if risk_count >= 2:
            risk_indicators["has_multiple_risks"] = True
            risk_indicators["risk_score"] += 0.2
        
        # 限制风险分数在 0-1 之间
        risk_indicators["risk_score"] = min(risk_indicators["risk_score"], 1.0)
        
        return risk_indicators
    
    def _get_minimal_parsed_data(self, message: Message) -> Dict[str, Any]:
        """
        获取最小解析数据（当完整解析失败时）
        
        Args:
            message: Telegram 消息对象
        
        Returns:
            最小数据字典
        """
        return {
            "message_id": message.message_id,
            "date": message.date,
            "text": message.text,
            "caption": message.caption,
            "from_user": format_user_info(message.from_user),
            "error": "消息解析失败，返回最小数据"
        }


# 创建全局解析器实例
message_parser = MessageParser()
