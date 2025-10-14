"""
Telegram 垃圾消息过滤机器人主程序
"""
import logging
import sys
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes
)
from telegram.error import TelegramError
import config
from spam_detector import spam_detector

# 配置日志
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=getattr(logging, config.LOG_LEVEL)
)
logger = logging.getLogger(__name__)


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


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    处理群组消息
    """
    message = update.message
    
    # 只处理群组消息
    if message.chat.type not in ['group', 'supergroup']:
        return
    
    try:
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
        
        # 在控制台打印每条消息的置信度
        print(f"\n{'='*80}")
        print(f"📨 新消息检测")
        print(f"👤 用户: {user.username or user.first_name} (ID: {user.id})")
        print(f"💬 内容: {message.text[:100] if message.text else '[非文本消息]'}{'...' if message.text and len(message.text) > 100 else ''}")
        print(f"🎯 垃圾消息判定: {'是 ❌' if result['is_spam'] else '否 ✅'}")
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
                # 删除消息
                await message.delete()
                logger.info(f"已删除消息 - 消息 ID: {message.message_id}")
                
                # 封禁用户
                await context.bot.ban_chat_member(
                    chat_id=message.chat_id,
                    user_id=user.id
                )
                logger.info(f"已封禁用户 - {user.username or user.first_name} (ID: {user.id})")
                
                # 发送通知消息（可选）
                notification_text = (
                    f"⚠️ 检测到垃圾消息并已处理\n"
                    f"👤 用户: {user.username or user.first_name}\n"
                    f"📋 类型: {result.get('category', '未知')}\n"
                    f"📊 置信度: {result['confidence']:.0%}\n"
                    f"💬 理由: {result['reason']}"
                )
                
                # 发送通知并在 10 秒后自动删除
                notification = await context.bot.send_message(
                    chat_id=message.chat_id,
                    text=notification_text
                )
                
                # 10 秒后删除通知消息
                context.application.job_queue.run_once(
                    delete_notification,
                    when=10,
                    data={
                        'chat_id': message.chat_id,
                        'message_id': notification.message_id
                    }
                )
                
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


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理错误"""
    logger.error(f"更新 {update} 导致错误: {context.error}", exc_info=context.error)


def main():
    """主函数"""
    try:
        # 验证配置
        config.validate_config()
        
        logger.info("正在启动 Telegram 垃圾消息过滤机器人...")
        
        # 创建应用
        application = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()
        
        # 添加命令处理器
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("status", status_command))
        
        # 添加消息处理器（处理所有文本消息和媒体消息）
        application.add_handler(
            MessageHandler(
                filters.ALL & ~filters.COMMAND,
                handle_message
            )
        )
        
        # 添加错误处理器
        application.add_error_handler(error_handler)
        
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
