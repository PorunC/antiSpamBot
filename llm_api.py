"""
LLM API 调用模块
支持 OpenAI 及兼容 OpenAI 格式的 API
"""
import json
import logging
from openai import AsyncOpenAI
from typing import Dict, Any
import config

logger = logging.getLogger(__name__)


class LLMClient:
    """LLM API 客户端"""
    
    def __init__(self):
        """初始化 LLM 客户端"""
        self.client = AsyncOpenAI(
            api_key=config.LLM_API_KEY,
            base_url=config.LLM_API_BASE
        )
        self.model = config.LLM_MODEL
        logger.info(f"LLM Client 初始化完成 - 模型: {self.model}, Base URL: {config.LLM_API_BASE}")
    
    async def analyze_message(
        self, 
        message_text: str, 
        username: str = "未知", 
        user_id: int = 0,
        is_new_member: bool = False,
        risk_indicators: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        使用 LLM 分析消息内容
        
        Args:
            message_text: 消息文本
            username: 用户名
            user_id: 用户 ID
            is_new_member: 是否为新成员
            risk_indicators: 风险指标字典
        
        Returns:
            分析结果字典，包含 is_spam, confidence, reason, category
        """
        try:
            # 如果没有传入风险指标，使用空字典
            if risk_indicators is None:
                risk_indicators = {
                    "risk_score": 0.0,
                    "risk_flags": []
                }
            
            # 构建风险指标描述
            risk_desc = f"风险分数: {risk_indicators.get('risk_score', 0):.2f}"
            if risk_indicators.get('risk_flags'):
                risk_desc += f"\n风险标识: {', '.join(risk_indicators['risk_flags'])}"
            
            # 构建提示词
            prompt = config.SPAM_DETECTION_PROMPT.format(
                message_text=message_text,
                username=username,
                user_id=user_id,
                is_new_member=is_new_member,
                risk_indicators=risk_desc
            )
            
            logger.debug(f"正在分析消息，用户: {username} (ID: {user_id})")
            
            # 调用 LLM API
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "你是一个专业的内容审核助手，擅长识别垃圾消息和不当内容。"
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,  # 降低温度以获得更一致的结果
                max_tokens=500,
                response_format={"type": "json_object"}  # 要求返回 JSON 格式
            )
            
            # 解析响应
            result_text = response.choices[0].message.content.strip()
            logger.debug(f"LLM 响应: {result_text}")
            
            # 解析 JSON 响应
            result = json.loads(result_text)
            
            # 验证响应格式
            required_fields = ["is_spam", "confidence", "reason"]
            if not all(field in result for field in required_fields):
                logger.error(f"LLM 响应缺少必需字段: {result}")
                return self._get_default_result(error="响应格式错误")
            
            # 确保类型正确
            result["is_spam"] = bool(result["is_spam"])
            result["confidence"] = float(result["confidence"])
            result["reason"] = str(result["reason"])
            result["category"] = result.get("category", "other")
            
            logger.info(
                f"消息分析完成 - 用户: {username}, "
                f"垃圾消息: {result['is_spam']}, "
                f"置信度: {result['confidence']:.2f}, "
                f"理由: {result['reason']}"
            )
            
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"解析 LLM 响应 JSON 失败: {e}")
            return self._get_default_result(error="JSON 解析失败")
        
        except Exception as e:
            logger.error(f"LLM API 调用失败: {e}", exc_info=True)
            return self._get_default_result(error=str(e))
    
    async def analyze_username(
        self,
        username: str,
        full_name: str,
        join_message: str,
        user_id: int
    ) -> Dict[str, Any]:
        """
        使用 LLM 检查用户入群时的用户名是否违规
        
        Args:
            username: Telegram 用户名
            full_name: 用户显示名称
            join_message: 入群系统消息文本
            user_id: 用户 ID
        
        Returns:
            分析结果字典，包含 is_violation, confidence, reason, category
        """
        try:
            formatted_username = username or "无用户名"
            formatted_full_name = full_name or "未知"
            formatted_join_message = join_message or ""
            
            prompt = config.USERNAME_CHECK_PROMPT.format(
                username=formatted_username,
                full_name=formatted_full_name,
                join_message=formatted_join_message,
                user_id=user_id
            )
            
            logger.debug(f"正在审核用户名，用户 ID: {user_id}, 用户名: {formatted_username}")
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "你是一个专业的群组安全审核助手，专注识别违规用户名。"
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.2,
                max_tokens=400,
                response_format={"type": "json_object"}
            )
            
            result_text = response.choices[0].message.content.strip()
            logger.debug(f"用户名审核 LLM 响应: {result_text}")
            
            result = json.loads(result_text)
            
            required_fields = ["is_violation", "confidence", "reason"]
            if not all(field in result for field in required_fields):
                logger.error(f"用户名审核响应缺少必需字段: {result}")
                return self._get_default_username_result(error="响应格式错误")
            
            result["is_violation"] = bool(result["is_violation"])
            result["confidence"] = float(result["confidence"])
            result["reason"] = str(result["reason"])
            result["category"] = result.get("category", "other")
            
            logger.info(
                f"用户名审核完成 - 用户 ID: {user_id}, 用户名: {formatted_username}, "
                f"违规: {result['is_violation']}, 置信度: {result['confidence']:.2f}, "
                f"理由: {result['reason']}"
            )
            
            return result
        
        except json.JSONDecodeError as e:
            logger.error(f"解析用户名审核 LLM 响应 JSON 失败: {e}")
            return self._get_default_username_result(error="JSON 解析失败")
        
        except Exception as e:
            logger.error(f"用户名审核 LLM 调用失败: {e}", exc_info=True)
            return self._get_default_username_result(error=str(e))
    
    def _get_default_result(self, error: str = "") -> Dict[str, Any]:
        """
        返回默认结果（当 API 调用失败时）
        
        Args:
            error: 错误信息
        
        Returns:
            默认结果字典
        """
        return {
            "is_spam": False,
            "confidence": 0.0,
            "reason": f"API 调用失败: {error}",
            "category": "error"
        }
    
    def _get_default_username_result(self, error: str = "") -> Dict[str, Any]:
        """
        返回用户名审核的默认结果
        
        Args:
            error: 错误信息
        
        Returns:
            默认结果字典
        """
        return {
            "is_violation": False,
            "confidence": 0.0,
            "reason": f"API 调用失败: {error}",
            "category": "error"
        }


# 创建全局 LLM 客户端实例
llm_client = LLMClient()
