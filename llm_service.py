"""
LLM服务模块 - 接入阿里云Qwen大模型
使用OpenAI兼容接口调用DashScope
"""

from openai import OpenAI
from config import config


class QwenService:
    """Qwen大模型服务"""

    def __init__(self):
        self.client = OpenAI(
            api_key=config.QWEN_API_KEY,
            base_url=config.QWEN_BASE_URL,
        )
        self.model = config.QWEN_MODEL

    def chat(self, system_prompt: str, user_message: str) -> str:
        """
        发送聊天请求到Qwen

        Args:
            system_prompt: 系统提示词
            user_message: 用户消息

        Returns:
            模型回复内容
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.7,
                max_tokens=2000,
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"LLM调用失败: {str(e)}"

    def analyze_food_request(self, user_input: str) -> dict:
        """
        分析用户的美食需求，提取关键信息

        Returns:
            包含口味、预算、菜系等信息的字典
        """
        system_prompt = """你是一个美食需求分析助手。请从用户的描述中提取以下信息，并以JSON格式返回：
{
    "taste": "口味偏好，如：清淡、辣、甜、咸、酸等，没有则为null",
    "budget_min": "最低预算(数字)，没有则为null",
    "budget_max": "最高预算(数字)，没有则为null",
    "cuisine": "菜系偏好，如：中餐、西餐、日料、韩餐等，没有则为null",
    "keywords": ["其他关键词列表"],
    "meal_time": "用餐时间，如：早餐、午餐、晚餐、夜宵，没有则为null"
}
只返回JSON，不要其他内容。"""

        response = self.chat(system_prompt, user_input)

        # 尝试解析JSON
        import json
        try:
            # 清理可能的markdown标记
            cleaned = response.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[1]
            if cleaned.endswith("```"):
                cleaned = cleaned.rsplit("```", 1)[0]
            cleaned = cleaned.strip()
            return json.loads(cleaned)
        except json.JSONDecodeError:
            return {
                "taste": None,
                "budget_min": None,
                "budget_max": None,
                "cuisine": None,
                "keywords": [],
                "meal_time": None,
                "raw_response": response
            }


# 单例
qwen_service = QwenService()
