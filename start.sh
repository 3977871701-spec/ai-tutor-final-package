#!/bin/bash

# AI辅导员系统启动脚本

set -e

cd "$(dirname "$0")"

echo "=========================================="
echo "   学院嵌入公众号AI辅导员系统"
echo "=========================================="
echo ""

# 1. 检查Python依赖
echo "[1/4] 检查Python依赖..."
if ! command -v python3 &> /dev/null; then
    echo "错误: Python3 未安装"
    exit 1
fi

# 2. 创建必要目录
echo "[2/4] 创建数据目录..."
mkdir -p data/chroma_db
mkdir -p knowledge/uploads
mkdir -p logs

# 3. 启动ngrok内网穿透（可选）
echo "[3/4] 检查ngrok配置..."
if command -v ngrok &> /dev/null; then
    if [ -n "$NGROK_AUTH_TOKEN" ]; then
        echo "启动ngrok内网穿透..."
        ngrok http 8000 --log=stdout > logs/ngrok.log 2>&1 &
        sleep 3
        echo "ngrok已启动，日志: logs/ngrok.log"
    else
        echo "注意: 未设置NGROK_AUTH_TOKEN，跳过ngrok启动"
        echo "如需公网访问，请手动启动: ngrok http 8000"
    fi
else
    echo "ngrok未安装，跳过"
fi

# 4. 启动FastAPI服务
echo "[4/4] 启动FastAPI服务..."
echo ""
echo "服务地址: http://localhost:8000"
echo "API文档: http://localhost:8000/docs"
echo ""
echo "按Ctrl+C停止服务"
echo ""

# 创建日志目录
mkdir -p logs

# 使用uvicorn启动
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --log-level info
