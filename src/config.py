"""
配置模块：从 .env 读取 DeepSeek API Key 等配置。
"""

import os
from dotenv import load_dotenv

# 项目根目录
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 加载项目根目录下的 .env 文件
load_dotenv(os.path.join(_PROJECT_ROOT, ".env"))

# DeepSeek API 配置
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv(
    "DEEPSEEK_BASE_URL", "https://api.deepseek.com"
)
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

# 默认工作文件夹：项目根目录下的 agent_work
WORKSPACE_ROOT = os.getenv(
    "WORKSPACE_ROOT",
    os.path.join(_PROJECT_ROOT, "agent_work"),
)


def validate_config() -> None:
    """
    校验必要配置，缺失时给出明确提示。
    """
    if not DEEPSEEK_API_KEY:
        raise RuntimeError(
            "未找到 DEEPSEEK_API_KEY，请在项目根目录的 .env 文件中配置。"
        )
