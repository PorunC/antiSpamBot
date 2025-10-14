"""
垃圾消息检测模块
"""
import logging
from typing import Dict, Any
from telegram import Message, User
from llm_api import llm_client
import config

logger = logging.getLogger(__name__)


class SpamDetector:
    """垃圾消息检测器"""
    
    def __init__(self):
        """初始化检测器"""
        self.confidence_threshold = config.CONFIDENCE_THRESHOLD
        self.admin_user_ids = set(config.ADMIN_USER_IDS)
        logger.info(f"垃圾消息检测器初始化完成 - 置信度阈值: {self.confidence_threshold}")
    
    async def check_message(self, message: Message) -> Dict[str, Any]:
        """
        检查消息是否为垃圾消息
        
        Args:
            message: Telegram 消息对象
        
        Returns:
            检测结果字典，包含:
            - should_delete: 是否应该删除
            - should_ban: 是否应该封禁用户
            - result: LLM 分析结果
            - skip_reason: 跳过检测的原因（如果有）
        """
        user: User = message.from_user
        
        # 检查是否为管理员
        if user.id in self.admin_user_ids:
            logger.info(f"跳过管理员消息 - 用户: {user.username} (ID: {user.id})")
            return {
                "should_delete": False,
                "should_ban": False,
                "result": None,
                "skip_reason": "管理员用户"
            }
        
        # 检查消息是否为机器人发送
        if user.is_bot:
            logger.debug(f"跳过机器人消息 - 用户: {user.username}")
            return {
                "should_delete": False,
                "should_ban": False,
                "result": None,
                "skip_reason": "机器人消息"
            }
        
        # 获取消息文本
        message_text = self._extract_message_text(message)
        
        if not message_text:
            logger.debug("消息无文本内容，跳过检测")
            return {
                "should_delete": False,
                "should_ban": False,
                "result": None,
                "skip_reason": "无文本内容"
            }
        
        # 检查是否为新成员（加入群组后的第一条消息）
        is_new_member = self._is_new_member_message(message)
        
        # 使用 LLM 分析消息
        username = user.username or user.first_name or "未知用户"
        result = await llm_client.analyze_message(
            message_text=message_text,
            username=username,
            user_id=user.id,
            is_new_member=is_new_member
        )
        
        # 判断是否应该删除和封禁
        should_delete = (
            result["is_spam"] and 
            result["confidence"] >= self.confidence_threshold
        )
        should_ban = should_delete  # 如果删除消息，同时封禁用户
        
        logger.info(
            f"检测结果 - 用户: {username} (ID: {user.id}), "
            f"删除: {should_delete}, 封禁: {should_ban}, "
            f"置信度: {result['confidence']:.2f}, "
            f"理由: {result['reason']}"
        )
        
        return {
            "should_delete": should_delete,
            "should_ban": should_ban,
            "result": result,
            "skip_reason": None
        }
    
    def _extract_message_text(self, message: Message) -> str:
        """
        提取消息文本内容
        
        Args:
            message: Telegram 消息对象
        
        Returns:
            消息文本
        """
        text_parts = []
        
        # 普通文本
        if message.text:
            text_parts.append(message.text)
        
        # 图片说明
        if message.caption:
            text_parts.append(message.caption)
        
        # 联系人信息
        if message.contact:
            text_parts.append(
                f"联系人: {message.contact.first_name} "
                f"{message.contact.last_name or ''} "
                f"{message.contact.phone_number or ''}"
            )
        
        # 位置信息
        if message.location:
            text_parts.append(
                f"位置: 纬度 {message.location.latitude}, "
                f"经度 {message.location.longitude}"
            )
        
        return " ".join(text_parts)
    
    def _is_new_member_message(self, message: Message) -> bool:
        """
        判断是否为新成员消息
        
        Args:
            message: Telegram 消息对象
        
        Returns:
            是否为新成员
        """
        # 检查是否有新成员加入的系统消息
        if message.new_chat_members:
            return True
        
        # 这里可以添加更多逻辑，比如检查用户加入时间
        # 但需要维护用户加入时间的数据库
        
        return False


# 创建全局检测器实例
spam_detector = SpamDetector()
