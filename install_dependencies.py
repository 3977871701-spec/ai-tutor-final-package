#!/usr/bin/env python3
"""
跨平台安装脚本
自动检测系统并安装依赖
"""

import os
import sys
import platform
import subprocess
from pathlib import Path


def is_windows():
    return platform.system() == "Windows"


def is_mac():
    return platform.system() == "Darwin"


def is_linux():
    return platform.system() == "Linux"


def run_command(cmd, check=True):
    """运行命令"""
    print(f"  执行: {' '.join(cmd)}")
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True
        )
        if result.returncode != 0 and check:
            print(f"  ⚠️  命令执行失败: {result.stderr[:200]}")
        return result.returncode == 0
    except Exception as e:
        print(f"  ❌ 错误: {e}")
        return False


def check_python():
    """检查Python"""
    version = sys.version_info
    print(f"\n🐍 Python版本: {version.major}.{version.minor}.{version.micro}")
    
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("❌ 需要 Python 3.8+")
        return False
    
    print("✅ Python版本符合要求")
    return True


def check_pip():
    """检查pip"""
    print("\n📦 检查pip...")
    
    if is_windows():
        cmd = [sys.executable, "-m", "pip", "--version"]
    else:
        cmd = [sys.executable, "-m", "pip", "--version"]
    
    if run_command(cmd, check=False):
        print("✅ pip可用")
        return True
    else:
        print("❌ pip不可用")
        return False


def install_requirements():
    """安装依赖"""
    print("\n📥 安装Python依赖...")
    
    requirements_file = Path(__file__).parent / "requirements.txt"
    
    if not requirements_file.exists():
        print("❌ requirements.txt 不存在")
        return False
    
    # 安装命令
    cmd = [
        sys.executable,
        "-m", "pip",
        "install",
        "--upgrade", "pip"
    ]
    run_command(cmd, check=False)
    
    cmd = [
        sys.executable,
        "-m", "pip",
        "install",
        "-r", str(requirements_file)
    ]
    
    if run_command(cmd):
        print("✅ 依赖安装完成")
        return True
    else:
        print("❌ 依赖安装失败")
        return False


def create_directories():
    """创建必要目录"""
    print("\n📁 创建目录...")
    
    dirs = [
        "data",
        "data/chroma_db",
        "knowledge",
        "knowledge/uploads",
        "logs",
    ]
    
    for d in dirs:
        path = Path(__file__).parent / d
        path.mkdir(parents=True, exist_ok=True)
        print(f"  ✅ {d}/")


def download_model():
    """下载HuggingFace模型（显示进度）"""
    print("\n🤗 检查/下载嵌入模型...")
    
    model_name = "paraphrase-multilingual-MiniLM-L12-v2"
    
    # 设置环境变量
    os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
    
    try:
        from sentence_transformers import SentenceTransformer
        
        print(f"  正在加载模型: {model_name}")
        model = SentenceTransformer(model_name)
        print("  ✅ 模型加载成功")
        return True
    except Exception as e:
        print(f"  ⚠️ 模型加载结果: {e}")
        print("  (如模型未缓存，系统会自动下载)")
        return True  # 不强制要求成功


def main():
    print("=" * 50)
    print("   学院嵌入公众号AI辅导员系统")
    print("   跨平台安装脚本")
    print("=" * 50)
    
    print(f"\n🖥️  操作系统: {platform.system()} {platform.release()}")
    
    # 1. 检查Python
    if not check_python():
        sys.exit(1)
    
    # 2. 检查pip
    check_pip()
    
    # 3. 创建目录
    create_directories()
    
    # 4. 安装依赖
    install_requirements()
    
    # 5. 下载模型
    download_model()
    
    print("\n" + "=" * 50)
    print("✅ 安装完成！")
    print("=" * 50)
    print("\n下一步:")
    print("  1. 编辑 config.yaml 填入配置参数")
    print("  2. 运行: python -m uvicorn app.main:app --reload")
    print("     或双击: start.bat (Windows)")
    print("     或运行: ./start.sh (macOS/Linux)")


if __name__ == "__main__":
    main()
