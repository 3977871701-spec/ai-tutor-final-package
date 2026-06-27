@echo off
chcp 65001 >nul
title AI辅导员系统

echo ==========================================
echo    学院嵌入公众号AI辅导员系统
echo ==========================================
echo.

REM 1. 检查Python
echo [1/4] 检查Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo 错误: Python 未安装
    echo 请访问 https://www.python.org/downloads/ 下载安装
    pause
    exit /b 1
)

REM 2. 创建目录
echo [2/4] 创建数据目录...
if not exist "data\chroma_db" mkdir "data\chroma_db"
if not exist "knowledge\uploads" mkdir "knowledge\uploads"
if not exist "logs" mkdir "logs"

REM 3. 安装依赖
echo [3/4] 检查依赖...
python -m pip install -r requirements.txt --quiet >nul 2>&1
if errorlevel 1 (
    echo 警告: 依赖安装可能有问题
)

REM 4. 启动服务
echo.
echo [4/4] 启动服务...
echo.
echo 服务地址: http://localhost:8000
echo API文档: http://localhost:8000/docs
echo.
echo 按 Ctrl+C 停止服务
echo.

python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

pause
