"""
垃圾消息检测模块
"""
import logging
from typing import Dict, Any
from telegram import Message, User
from llm_api import llm_client
from message_parser import message_parser
import config

logger = logging.getLogger(__name__)


class SpamDetector:
    """垃圾消息检测器"""
    
    def __init__(self):
        """初始化检测器"""
        self.confidence_threshold = config.CONFIDENCE_THRESHOLD
        self.admin_user_ids = set(config.ADMIN_USER_IDS)
        self.system_user_ids = set(config.SYSTEM_USER_IDS)
        logger.info(f"垃圾消息检测器初始化完成 - 置信度阈值: {self.confidence_threshold}")
        logger.info(f"系统白名单用户: {self.system_user_ids}")
    
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
        
        # 检查是否为系统白名单用户（Telegram 官方账号等）
        if user.id in self.system_user_ids:
            logger.info(f"跳过系统白名单用户 - 用户: {user.username or user.first_name} (ID: {user.id})")
            return {
                "should_delete": False,
                "should_ban": False,
                "result": None,
                "skip_reason": "系统白名单用户"
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
        
        # 使用新的消息解析器解析完整消息
        parsed_message = message_parser.parse_message(message)
        
        # 合并白名单用户ID（管理员 + 系统白名单）
        whitelist_user_ids = self.admin_user_ids | self.system_user_ids
        
        # 格式化消息用于分析（传入白名单用户ID）
        message_text = message_parser.format_for_analysis(
            parsed_message,
            whitelist_user_ids=whitelist_user_ids
        )
        
        # 提取风险指标
        risk_indicators = message_parser.extract_risk_indicators(parsed_message)
        
        if not message_text:
            logger.debug("消息无可分析内容，跳过检测")
            return {
                "should_delete": False,
                "should_ban": False,
                "result": None,
                "skip_reason": "无可分析内容",
                "parsed_message": parsed_message,
                "risk_indicators": risk_indicators
            }
        
        # 检查是否为新成员（加入群组后的第一条消息）
        is_new_member = self._is_new_member_message(message)
        
        # 使用 LLM 分析消息
        username = user.username or user.first_name or "未知用户"
        result = await llm_client.analyze_message(
            message_text=message_text,
            username=username,
            user_id=user.id,
            is_new_member=is_new_member,
            risk_indicators=risk_indicators
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
            f"风险分数: {risk_indicators['risk_score']:.2f}, "
            f"理由: {result['reason']}"
        )
        
        return {
            "should_delete": should_delete,
            "should_ban": should_ban,
            "result": result,
            "skip_reason": None,
            "parsed_message": parsed_message,
            "risk_indicators": risk_indicators
        }
    
    def _extract_message_text(self, message: Message) -> str:
        """
        提取消息文本内容（已弃用，保留用于兼容性）
        现在使用 message_parser 模块进行完整解析
        
        Args:
            message: Telegram 消息对象
        
        Returns:
            消息文本
        """
        # 使用新的解析器
        parsed_message = message_parser.parse_message(message)
        return message_parser.format_for_analysis(parsed_message)
    
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
