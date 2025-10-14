"""
测试脚本 - 用于测试 LLM API 和垃圾消息检测功能
不需要实际的 Telegram 连接
"""
import asyncio
import logging
from llm_api import llm_client
import config

# 配置日志
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


# 测试消息样本
TEST_MESSAGES = [
    {
        "text": "大家好，我是新来的，很高兴认识大家！",
        "username": "test_user_1",
        "user_id": 12345,
        "expected": "正常消息",
    },
    {
        "text": "加微信 wxid_123456 免费领取资料，仅限今天！",
        "username": "spammer_1",
        "user_id": 67890,
        "expected": "垃圾消息（广告）",
    },
    {
        "text": "点击链接 http://scam-site.com 获得超值优惠，限时特价！",
        "username": "spammer_2",
        "user_id": 11111,
        "expected": "垃圾消息（诈骗链接）",
    },
    {
        "text": "今天天气不错，有人要一起去爬山吗？",
        "username": "test_user_2",
        "user_id": 22222,
        "expected": "正常消息",
    },
    {
        "text": "想要了解兼职机会的私聊我，日赚500+不是梦",
        "username": "spammer_3",
        "user_id": 33333,
        "expected": "垃圾消息（招聘诈骗）",
    },
    {
        "text": "有人知道这个问题怎么解决吗？谢谢大家",
        "username": "test_user_3",
        "user_id": 44444,
        "expected": "正常消息",
    },
    {
        "text": "扫码进群，海量资源分享📱💰🔥",
        "username": "spammer_4",
        "user_id": 55555,
        "expected": "垃圾消息（拉群）",
    },
]


async def test_message(message_data: dict):
    """测试单条消息"""
    print(f"\n{'='*60}")
    print(f"📝 测试消息: {message_data['text']}")
    print(f"👤 用户: {message_data['username']} (ID: {message_data['user_id']})")
    print(f"🎯 预期结果: {message_data['expected']}")
    print(f"{'-'*60}")
    
    result = await llm_client.analyze_message(
        message_text=message_data['text'],
        username=message_data['username'],
        user_id=message_data['user_id'],
        is_new_member=False
    )
    
    print(f"🤖 LLM 判断:")
    print(f"   - 是否垃圾消息: {'是 ❌' if result['is_spam'] else '否 ✅'}")
    print(f"   - 置信度: {result['confidence']:.2%}")
    print(f"   - 类型: {result.get('category', 'N/A')}")
    print(f"   - 理由: {result['reason']}")
    
    # 判断是否会被处理
    should_delete = result['is_spam'] and result['confidence'] >= config.CONFIDENCE_THRESHOLD
    print(f"\n⚖️  处理结果:")
    print(f"   - 是否删除: {'是 🗑️' if should_delete else '否 ✅'}")
    print(f"   - 是否封禁: {'是 🚫' if should_delete else '否 ✅'}")
    
    return result


async def run_tests():
    """运行所有测试"""
    print("\n" + "="*60)
    print("🧪 Telegram 垃圾消息过滤机器人 - 测试程序")
    print("="*60)
    print(f"\n📊 配置信息:")
    print(f"   - LLM 模型: {config.LLM_MODEL}")
    print(f"   - API Base: {config.LLM_API_BASE}")
    print(f"   - 置信度阈值: {config.CONFIDENCE_THRESHOLD}")
    print(f"\n开始测试 {len(TEST_MESSAGES)} 条消息...\n")
    
    results = []
    correct_predictions = 0
    
    for i, message_data in enumerate(TEST_MESSAGES, 1):
        print(f"\n[{i}/{len(TEST_MESSAGES)}]", end=" ")
        try:
            result = await test_message(message_data)
            results.append((message_data, result))
            
            # 简单的准确性检查
            is_spam_expected = "垃圾消息" in message_data['expected']
            is_spam_detected = result['is_spam'] and result['confidence'] >= config.CONFIDENCE_THRESHOLD
            
            if is_spam_expected == is_spam_detected:
                correct_predictions += 1
            
            # 等待一下，避免 API 限流
            await asyncio.sleep(1)
            
        except Exception as e:
            logger.error(f"测试失败: {e}")
    
    # 打印总结
    print(f"\n\n{'='*60}")
    print("📊 测试总结")
    print(f"{'='*60}")
    print(f"✅ 总测试数: {len(TEST_MESSAGES)}")
    print(f"✅ 正确预测: {correct_predictions}")
    print(f"📈 准确率: {correct_predictions / len(TEST_MESSAGES):.1%}")
    print(f"\n💡 提示: 如果准确率不理想，可以:")
    print(f"   1. 调整 CONFIDENCE_THRESHOLD 值")
    print(f"   2. 修改 config.py 中的 SPAM_DETECTION_PROMPT")
    print(f"   3. 尝试使用更强大的模型")
    print(f"{'='*60}\n")


async def interactive_test():
    """交互式测试"""
    print("\n" + "="*60)
    print("🧪 交互式测试模式")
    print("="*60)
    print("输入要测试的消息内容（输入 'quit' 退出）\n")
    
    while True:
        try:
            message_text = input("📝 消息内容: ").strip()
            
            if message_text.lower() in ['quit', 'exit', 'q']:
                print("👋 退出测试模式")
                break
            
            if not message_text:
                continue
            
            print(f"\n正在分析...")
            result = await llm_client.analyze_message(
                message_text=message_text,
                username="test_user",
                user_id=99999,
                is_new_member=False
            )
            
            print(f"\n🤖 分析结果:")
            print(f"   - 是否垃圾消息: {'是 ❌' if result['is_spam'] else '否 ✅'}")
            print(f"   - 置信度: {result['confidence']:.2%}")
            print(f"   - 类型: {result.get('category', 'N/A')}")
            print(f"   - 理由: {result['reason']}")
            
            should_delete = result['is_spam'] and result['confidence'] >= config.CONFIDENCE_THRESHOLD
            print(f"   - 是否会被删除: {'是 🗑️' if should_delete else '否 ✅'}\n")
            
        except KeyboardInterrupt:
            print("\n\n👋 退出测试模式")
            break
        except Exception as e:
            logger.error(f"测试出错: {e}")


def main():
    """主函数"""
    try:
        # 验证配置
        config.validate_config()
        
        print("\n请选择测试模式:")
        print("1. 运行预设测试用例")
        print("2. 交互式测试")
        
        choice = input("\n请输入选项 (1/2): ").strip()
        
        if choice == "1":
            asyncio.run(run_tests())
        elif choice == "2":
            asyncio.run(interactive_test())
        else:
            print("❌ 无效选项")
    
    except ValueError as e:
        logger.error(f"❌ 配置错误: {e}")
        print("\n请先配置 .env 文件！")
        print("运行 'cp .env.example .env' 然后编辑 .env 文件")
    except Exception as e:
        logger.error(f"❌ 测试失败: {e}", exc_info=True)


if __name__ == '__main__':
    main()
