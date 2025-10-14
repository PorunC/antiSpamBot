# 常见问题解答（FAQ）

## 安装和配置

### Q1: 我需要什么才能运行这个机器人？

**A:** 你需要：
1. Python 3.8+ 环境
2. 一个 Telegram Bot Token（从 @BotFather 获取）
3. 一个 LLM API 密钥（OpenAI、Claude、智谱 AI 等）
4. 一台服务器或本地电脑（保持运行）

### Q2: 如何获取 Telegram Bot Token？

**A:** 
1. 在 Telegram 搜索 `@BotFather`
2. 发送 `/newbot` 命令
3. 按提示设置机器人名称和用户名
4. 保存 Token（格式：`1234567890:ABCdefGHIjklMNOpqrsTUVwxyz`）

### Q3: 支持哪些 LLM API？

**A:** 支持所有兼容 OpenAI API 格式的服务：
- **OpenAI**: GPT-4, GPT-3.5
- **Anthropic Claude**: 通过 OpenRouter
- **智谱 AI**: GLM-4
- **阿里云**: 通义千问
- **DeepSeek**: DeepSeek-Chat
- **其他**: 任何兼容 OpenAI API 格式的服务

### Q4: 哪个 LLM 最便宜/最好？

**A:** 推荐选择：
- **性价比最高**: DeepSeek (￥0.001/千 tokens)
- **最便宜**: 智谱 GLM-4-Flash (免费额度)
- **最准确**: GPT-4o (但贵)
- **平衡**: GPT-4o-mini 或 GLM-4

### Q5: 如何获取我的 Telegram 用户 ID？

**A:** 
1. 搜索 `@userinfobot`
2. 发送 `/start`
3. 机器人会返回你的用户 ID

## 使用问题

### Q6: 机器人提示 "not enough rights" 错误

**A:** 机器人没有足够权限。解决方法：
1. 进入群组设置 → 管理员
2. 添加机器人为管理员
3. 确保勾选以下权限：
   - ✅ 删除消息
   - ✅ 封禁用户

### Q7: 机器人不响应消息

**A:** 检查以下几点：
1. 确认 `.env` 文件配置正确
2. 检查机器人是否在运行：`ps aux | grep bot.py`
3. 查看日志：`tail -f bot.log` 或控制台输出
4. 测试 Bot Token：`curl https://api.telegram.org/bot<YOUR_TOKEN>/getMe`

### Q8: 机器人误判率太高，总是删除正常消息

**A:** 调整配置：
1. 提高置信度阈值（.env 文件）：
   ```env
   CONFIDENCE_THRESHOLD=0.85  # 从 0.7 提高到 0.85
   ```
2. 修改检测提示词（`config.py` 中的 `SPAM_DETECTION_PROMPT`）
3. 使用更强大的 LLM 模型

### Q9: 机器人漏判，很多垃圾消息没被删除

**A:** 
1. 降低置信度阈值：
   ```env
   CONFIDENCE_THRESHOLD=0.6  # 从 0.7 降低到 0.6
   ```
2. 优化提示词，增加具体的垃圾消息特征
3. 考虑使用更智能的模型（如 GPT-4）

### Q10: 如何设置管理员白名单？

**A:** 在 `.env` 文件中添加：
```env
ADMIN_USER_IDS=123456789,987654321,111222333
```
用逗号分隔多个用户 ID。这些用户的消息不会被检测。

## 技术问题

### Q11: LLM API 调用失败

**A:** 检查：
1. API Key 是否正确
2. API Base URL 是否正确
3. 账户是否有足够额度
4. 网络是否能访问 API（国内可能需要代理）

示例测试命令：
```bash
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer YOUR_API_KEY"
```

### Q12: 如何查看详细日志？

**A:** 
1. 启动时在控制台会显示日志
2. 或者重定向到文件：
   ```bash
   python bot.py > bot.log 2>&1
   ```
3. 修改日志级别（`config.py`）：
   ```python
   LOG_LEVEL = "DEBUG"  # 显示更详细的日志
   ```

### Q13: 机器人占用内存/CPU 过高

**A:** 
1. 检查是否有内存泄漏
2. 限制并发处理的消息数量
3. 使用更轻量的 LLM 模型
4. 考虑增加服务器配置

### Q14: 如何在后台运行机器人？

**A:** 多种方法：

**方法 1: systemd（推荐）**
```bash
sudo systemctl start telegram-spam-filter
```

**方法 2: screen**
```bash
screen -S bot
python bot.py
# 按 Ctrl+A 然后 D 分离
```

**方法 3: nohup**
```bash
nohup python bot.py > bot.log 2>&1 &
```

**方法 4: Docker**
```bash
docker-compose up -d
```

### Q15: 如何停止机器人？

**A:** 
- **直接运行**: 按 `Ctrl+C`
- **systemd**: `sudo systemctl stop telegram-spam-filter`
- **screen**: `screen -X -S bot quit`
- **nohup**: `pkill -f bot.py`
- **Docker**: `docker-compose down`

## 部署问题

### Q16: 可以部署在免费服务器上吗？

**A:** 可以，但有限制：
- **Heroku**: 免费层每月有小时限制
- **Railway**: 有免费额度
- **Oracle Cloud**: 有永久免费层
- **本地电脑**: 需要保持开机

注意：LLM API 调用会产生费用。

### Q17: 需要什么配置的服务器？

**A:** 最低要求：
- **CPU**: 1 核
- **内存**: 512MB
- **存储**: 1GB
- **网络**: 稳定的互联网连接

推荐配置：
- **CPU**: 1-2 核
- **内存**: 1-2GB
- **存储**: 5GB

### Q18: 如何更新机器人？

**A:** 
1. 停止机器人
2. 备份配置文件（.env）
3. 下载/拉取最新代码
4. 安装新依赖：`pip install -r requirements.txt`
5. 重启机器人

详细步骤见 `DEPLOYMENT.md`。

### Q19: 可以同时监控多个群组吗？

**A:** 可以！只需将机器人添加到多个群组即可，同一个机器人可以同时监控多个群组。

### Q20: 如何备份机器人配置？

**A:** 
```bash
# 备份 .env 文件
cp .env .env.backup

# 或使用脚本定期备份
crontab -e
# 添加: 0 2 * * * cp /path/to/bot/.env /backup/env_$(date +\%Y\%m\%d).backup
```

## 性能和成本

### Q21: 使用机器人的成本是多少？

**A:** 主要成本：
1. **LLM API 费用**: 取决于消息量和模型
   - 小群（<100 消息/天）：约 ￥1-5/月
   - 中群（100-1000 消息/天）：约 ￥5-50/月
   - 大群（>1000 消息/天）：约 ￥50-500/月

2. **服务器费用**: 
   - 免费层：￥0
   - VPS: ￥10-50/月

### Q22: 如何降低 API 调用成本？

**A:** 
1. 使用更便宜的模型（DeepSeek、GLM-4-Flash）
2. 提高置信度阈值，减少误判
3. 添加本地预过滤规则
4. 使用缓存机制
5. 只检测特定类型的消息（如包含链接的）

### Q23: 检测一条消息需要多长时间？

**A:** 通常：
- **LLM API 调用**: 0.5-2 秒
- **消息删除**: <0.1 秒
- **总计**: 约 1-3 秒

可以通过使用更快的模型或本地预过滤来优化。

## 安全和隐私

### Q24: 机器人会存储用户消息吗？

**A:** 默认不会。消息仅发送到 LLM API 进行分析，不会存储在本地。如果需要审计日志，可以自行修改代码添加记录功能。

### Q25: LLM API 会看到用户消息吗？

**A:** 是的，消息会发送到 LLM API 进行分析。请选择可信赖的 LLM 服务商，并查看其隐私政策。

### Q26: 如何防止机器人被滥用？

**A:** 
1. 设置管理员白名单
2. 只在可信的群组中使用
3. 定期检查日志
4. 限制 API 调用频率
5. 设置合理的置信度阈值

### Q27: Token 泄露了怎么办？

**A:** 
1. 立即在 @BotFather 中重新生成 Token：
   - 发送 `/mybots`
   - 选择你的机器人
   - 选择 "API Token" → "Revoke current token"
2. 更新 .env 文件
3. 重启机器人

## 高级功能

### Q28: 可以自定义检测规则吗？

**A:** 可以！修改 `config.py` 中的 `SPAM_DETECTION_PROMPT` 提示词，添加你的特定规则。

### Q29: 如何添加统计功能？

**A:** 可以修改代码添加数据库（如 SQLite），记录：
- 检测到的垃圾消息数量
- 被封禁的用户
- 检测准确率
- 等等

### Q30: 可以只删除消息而不踢人吗？

**A:** 可以！修改 `spam_detector.py` 中的检测逻辑：
```python
return {
    "should_delete": should_delete,
    "should_ban": False,  # 改为 False
    "result": result,
    "skip_reason": None
}
```

### Q31: 如何添加白名单关键词？

**A:** 在 `spam_detector.py` 中添加逻辑：
```python
WHITELIST_KEYWORDS = ["官方公告", "管理员通知"]

if any(keyword in message_text for keyword in WHITELIST_KEYWORDS):
    return {
        "should_delete": False,
        "should_ban": False,
        "result": None,
        "skip_reason": "白名单关键词"
    }
```

### Q32: 可以集成其他反垃圾服务吗？

**A:** 可以！在检测流程中添加其他 API 调用，例如：
- Akismet
- Google Safe Browsing
- 自定义黑名单数据库

## 故障排除

### Q33: 出现 "module not found" 错误

**A:** 
```bash
# 重新安装依赖
pip install -r requirements.txt

# 或激活虚拟环境
source venv/bin/activate  # macOS/Linux
venv\Scripts\activate     # Windows
```

### Q34: 出现编码错误

**A:** 确保文件使用 UTF-8 编码，Python 脚本开头添加：
```python
# -*- coding: utf-8 -*-
```

### Q35: API 超时怎么办？

**A:** 
1. 检查网络连接
2. 增加超时时间（修改 `llm_api.py`）
3. 使用更快的 API 服务
4. 添加重试逻辑

## 其他问题

### Q36: 可以用于商业用途吗？

**A:** 可以，但请注意：
1. 遵守 Telegram 服务条款
2. 遵守 LLM API 服务条款
3. 确保符合当地法律法规

### Q37: 如何贡献代码？

**A:** 欢迎贡献！
1. Fork 项目
2. 创建分支
3. 提交更改
4. 发起 Pull Request

### Q38: 在哪里获取帮助？

**A:** 
1. 查看项目文档（README.md、QUICKSTART.md、DEPLOYMENT.md）
2. 查看日志文件
3. 提交 Issue
4. 加入社区讨论

### Q39: 项目有 GUI 界面吗？

**A:** 目前没有，是纯命令行工具。可以考虑添加：
- Web 管理面板
- Telegram 管理命令
- 统计仪表板

### Q40: 未来会添加什么功能？

**A:** 可能的改进：
- [ ] 支持图片内容检测
- [ ] 用户行为分析
- [ ] 机器学习模型训练
- [ ] Web 管理界面
- [ ] 多语言支持
- [ ] 统计和报表
- [ ] 黑名单/白名单管理
- [ ] 自定义处理规则

---

**还有其他问题？** 请提交 Issue 或查看项目文档！
