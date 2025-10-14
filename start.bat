@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo 🤖 Telegram 垃圾消息过滤机器人 - 安装向导
echo ========================================
echo.

REM 检查 Python 是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 错误: 未找到 Python 3
    echo 请先安装 Python 3.8 或更高版本
    pause
    exit /b 1
)

for /f "tokens=*" %%i in ('python --version') do set PYTHON_VERSION=%%i
echo ✅ Python 版本: !PYTHON_VERSION!
echo.

REM 创建虚拟环境
if not exist "venv" (
    echo 📦 正在创建虚拟环境...
    python -m venv venv
    echo ✅ 虚拟环境创建完成
) else (
    echo ✅ 虚拟环境已存在
)
echo.

REM 激活虚拟环境
echo 🔧 激活虚拟环境...
call venv\Scripts\activate.bat

REM 安装依赖
echo 📥 正在安装依赖包...
python -m pip install --upgrade pip
pip install -r requirements.txt
echo ✅ 依赖包安装完成
echo.

REM 检查 .env 文件
if not exist ".env" (
    echo ⚠️  未找到 .env 文件
    echo 正在从 .env.example 创建 .env 文件...
    copy .env.example .env
    echo ✅ .env 文件已创建
    echo.
    echo ⚠️  请编辑 .env 文件，填入你的配置信息：
    echo    1. TELEGRAM_BOT_TOKEN - 从 @BotFather 获取
    echo    2. LLM_API_KEY - 你的 LLM API 密钥
    echo    3. LLM_API_BASE - API 基础 URL（可选）
    echo    4. LLM_MODEL - 使用的模型名称（可选）
    echo.
    echo 编辑完成后，运行: start.bat
    echo.
    pause
) else (
    echo ✅ .env 文件已存在
    echo.
    echo 🚀 准备启动机器人...
    echo 按 Ctrl+C 可以停止机器人
    echo.
    timeout /t 2 >nul
    python bot.py
    pause
)
