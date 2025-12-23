"""
配置文件 - 存放API密钥和配置项
"""
import os
from dataclasses import dataclass
from dotenv import load_dotenv

# 加载.env文件
load_dotenv()


@dataclass
class Config:
    # 阿里云 Qwen API配置 (DashScope)
    # 获取方式: https://dashscope.console.aliyun.com/
    QWEN_API_KEY: str = os.getenv("QWEN_API_KEY", "your-qwen-api-key")
    QWEN_MODEL: str = os.getenv("QWEN_MODEL", "qwen-plus")
    QWEN_BASE_URL: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"

    # 百度地图API配置
    # 获取方式: https://lbsyun.baidu.com/apiconsole/key
    BAIDU_MAP_AK: str = os.getenv("BAIDU_MAP_AK", "your-baidu-map-ak")

    # Agent服务配置
    AGENT_HOST: str = os.getenv("AGENT_HOST", "0.0.0.0")
    AGENT_PORT: int = int(os.getenv("AGENT_PORT", "8080"))


config = Config()
