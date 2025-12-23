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

    def generate_recommendation(self, user_input: str, restaurants: list) -> str:
        """
        根据餐厅数据生成智能推荐文案

        Args:
            user_input: 用户原始输入
            restaurants: 餐厅列表数据

        Returns:
            格式化的推荐文案
        """
        system_prompt = """你是一个专业的美食推荐助手。请根据用户的需求和提供的餐厅数据，生成友好、专业的推荐回复。

要求：
1. 回复要简洁但信息丰富
2. 突出每家餐厅的特色和与用户需求的匹配点
3. 使用markdown格式，让推荐更美观
4. 如果数据较少，可以适当补充建议
5. 回复使用中文"""

        # 构建餐厅信息
        restaurant_info = ""
        for i, r in enumerate(restaurants[:5], 1):
            restaurant_info += f"""
餐厅{i}:
- 名称: {r.get('name', '未知')}
- 类型: {r.get('type', '未知')}
- 地址: {r.get('address', '未知')}
- 评分: {r.get('rating', '暂无')}
- 人均: {r.get('cost', '暂无')}元
- 距离: {r.get('distance', '未知')}
- 电话: {r.get('tel', '暂无')}
"""

        user_message = f"""用户需求: {user_input}

可选餐厅数据:
{restaurant_info if restaurant_info else "暂无匹配的餐厅数据"}

请生成推荐回复。"""

        return self.chat(system_prompt, user_message)

    def generate_detail_description(self, restaurant: dict) -> str:
        """
        为餐厅生成详细描述

        Args:
            restaurant: 餐厅数据

        Returns:
            详细描述文案
        """
        system_prompt = """你是一个美食点评助手。请根据提供的餐厅信息，生成一段吸引人的餐厅介绍。
要求简洁、专业、有吸引力。使用markdown格式。"""

        restaurant_info = f"""
餐厅名称: {restaurant.get('name', '未知')}
类型: {restaurant.get('type', '未知')}
地址: {restaurant.get('address', '未知')}
评分: {restaurant.get('rating', '暂无')}
人均消费: {restaurant.get('cost', '暂无')}元
联系电话: {restaurant.get('tel', '暂无')}
营业时间: {restaurant.get('business_hours', '暂无')}
"""

        return self.chat(system_prompt, f"请为以下餐厅生成介绍:\n{restaurant_info}")


# 单例
qwen_service = QwenService()
