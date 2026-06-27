#!/usr/bin/env python3
"""
跨平台兼容性工具
提供Windows、macOS、Linux统一的路径和环境处理
"""

import os
import sys
import platform
import subprocess
from pathlib import Path
from typing import Optional, Tuple


def get_system_info() -> dict:
    """获取系统信息"""
    return {
        "system": platform.system(),  # Windows, Linux, Darwin
        "release": platform.release(),
        "version": platform.version(),
        "machine": platform.machine(),
        "python": sys.version,
    }


def is_windows() -> bool:
    """是否为Windows系统"""
    return platform.system() == "Windows"


def is_mac() -> bool:
    """是否为macOS系统"""
    return platform.system() == "Darwin"


def is_linux() -> bool:
    """是否为Linux系统"""
    return platform.system() == "Linux"


def get_project_root() -> Path:
    """获取项目根目录"""
    # 尝试多种方式获取项目根目录
    # 1. 当前文件向上查找
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "config.yaml").exists():
            return parent
        if (parent / "app").exists():
            return parent
    
    # 2. 回退到脚本执行目录
    if getattr(sys, 'frozen', False):
        # PyInstaller 打包
        return Path(sys.executable).parent
    else:
        return Path.cwd()


def get_data_dir() -> Path:
    """获取数据目录（跨平台）"""
    root = get_project_root()
    data_dir = root / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def get_cache_dir() -> Path:
    """获取缓存目录（跨平台）"""
    system = platform.system()
    
    if system == "Windows":
        base = Path(os.environ.get("LOCALAPPDATA", root / "AppData" / "Local"))
    elif system == "Darwin":
        base = Path.home() / "Library" / "Caches"
    else:
        base = Path.home() / ".cache"
    
    cache_dir = base / "ai-tutor"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def get_model_cache_path() -> Path:
    """获取HuggingFace模型缓存目录"""
    # 优先使用环境变量
    for env_var in ["TRANSFORMERS_CACHE", "HF_HOME", "HF_HUB_CACHE"]:
        if os.environ.get(env_var):
            return Path(os.environ[env_var])
    
    system = platform.system()
    
    if system == "Windows":
        return Path(os.environ.get("LOCALAPPDATA", "")) / "huggingface" / "hub"
    else:
        return Path.home() / ".cache" / "huggingface" / "hub"


def check_python_version(min_version: Tuple[int, int] = (3, 8)) -> Tuple[bool, str]:
    """检查Python版本"""
    version = sys.version_info[:2]
    if version >= min_version:
        return True, f"Python {version[0]}.{version[1]} ✓"
    return False, f"需要 Python {min_version[0]}.{min_version[1]}+，当前 {version[0]}.{version[1]}"


def check_command(command: str) -> Tuple[bool, str]:
    """检查命令是否可用（跨平台）"""
    try:
        if is_windows():
            result = subprocess.run(
                ["where", command],
                capture_output=True,
                text=True,
                shell=True
            )
        else:
            result = subprocess.run(
                ["which", command],
                capture_output=True,
                text=True
            )
        
        if result.returncode == 0:
            path = result.stdout.strip().split('\n')[0]
            return True, path
        return False, f"{command} 未找到"
    except:
        return False, f"无法检查 {command}"


def install_package(package: str) -> bool:
    """安装Python包（跨平台）"""
    try:
        if is_windows():
            subprocess.run([sys.executable, "-m", "pip", "install", package], check=True)
        else:
            subprocess.run([sys.executable, "-m", "pip", "install", package], check=True)
        return True
    except:
        return False


def run_command(command: list, cwd: Optional[Path] = None) -> Tuple[int, str, str]:
    """运行命令并返回结果（跨平台）"""
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True
        )
        return result.returncode, result.stdout, result.stderr
    except Exception as e:
        return -1, "", str(e)


def get_environment_info() -> dict:
    """获取完整环境信息"""
    return {
        "system": get_system_info(),
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "project_root": str(get_project_root()),
        "data_dir": str(get_data_dir()),
        "cache_dir": str(get_cache_dir()),
        "model_cache": str(get_model_cache_path()),
        "hf_endpoint": os.environ.get("HF_ENDPOINT", "未设置"),
        "transformers_offline": os.environ.get("TRANSFORMERS_OFFLINE", "未设置"),
    }


if __name__ == "__main__":
    print("=" * 50)
    print("系统环境信息")
    print("=" * 50)
    
    info = get_environment_info()
    
    print(f"\n操作系统: {info['system']['system']} {info['system']['release']}")
    print(f"Python版本: {info['python_version']}")
    print(f"项目目录: {info['project_root']}")
    print(f"数据目录: {info['data_dir']}")
    print(f"缓存目录: {info['cache_dir']}")
    print(f"模型缓存: {info['model_cache']}")
    print(f"HuggingFace端点: {info['hf_endpoint']}")
    
    print("\nPython版本检查:", check_python_version())
    print("pip可用:", check_command("pip"))
    print("python可用:", check_command("python3") or check_command("python"))
