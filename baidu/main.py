"""
外卖/美食助手 A2A Agent
接收主控Agent的结构化请求，执行skill并返回结果
"""

import json
import uuid
from datetime import datetime
from typing import Optional
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager

from config import config
from food_api_service import food_api_service


# ==================== Skill 实现 ====================

class FoodAgentSkills:
    """美食Agent技能 - 精简为3个核心技能"""

    def __init__(self):
        self.api = food_api_service
        self.default_city = "北京"

    def _format_restaurant(self, r: dict, index: int = None) -> str:
        """格式化单个餐厅信息"""
        prefix = f"{index}. " if index else ""
        lines = [
            f"**{prefix}{r.get('name', '未知')}**",
            f"   类型: {r.get('type', '未知')}",
            f"   评分: {r.get('rating', '暂无')}",
            f"   人均: {r.get('cost', '暂无')}元",
            f"   地址: {r.get('address', '暂无')}",
        ]
        if r.get('distance'):
            lines.append(f"   距离: {r.get('distance')}")
        if r.get('tel') and r.get('tel') != '暂无':
            lines.append(f"   电话: {r.get('tel')}")
        return "\n".join(lines)

    def _format_restaurant_list(self, restaurants: list, limit: int = 10) -> str:
        """格式化餐厅列表"""
        result = []
        for i, r in enumerate(restaurants[:limit], 1):
            result.append(self._format_restaurant(r, i))
        return "\n\n".join(result)

    def _format_detail(self, r: dict) -> str:
        """格式化餐厅详情"""
        lines = [
            f"# {r.get('name', '未知')}",
            "",
            f"**类型**: {r.get('type', '未知')}",
            f"**评分**: {r.get('rating', '暂无')}",
            f"**人均**: {r.get('cost', '暂无')}元",
            f"**地址**: {r.get('address', '暂无')}",
            f"**电话**: {r.get('tel', '暂无')}",
            f"**营业时间**: {r.get('business_hours', '暂无')}",
        ]
        if r.get('tag'):
            lines.append(f"**特色**: {r.get('tag')}")
        return "\n".join(lines)

    async def recommend(self, params: dict) -> str:
        """
        推荐餐厅（统一入口）

        支持参数组合：
        - taste: 口味偏好（辣、清淡、鲜...）
        - budget_max: 预算上限
        - budget_min: 预算下限
        - cuisine: 菜系/分类（川菜、火锅、日料...）
        - location: 坐标
        - address: 地址
        - city: 城市
        - ip: IP地址
        """
        taste = params.get("taste")
        budget_max = params.get("budget_max")
        cuisine = params.get("cuisine") or params.get("category")

        # 解析位置
        location, city = await self.api.resolve_location(
            location=params.get("location"),
            address=params.get("address"),
            city=params.get("city"),
            ip=params.get("ip")
        )

        # 调用智能搜索
        result = await self.api.smart_search(
            location=location,
            taste=taste,
            cuisine=cuisine,
            budget_max=int(budget_max) if budget_max else None,
            city=city
        )

        restaurants = result.get("restaurants", [])

        if not restaurants:
            return self._no_result_message(taste=taste, budget=budget_max, cuisine=cuisine)

        # 构建响应
        header = self._build_header(params, len(restaurants))
        body = self._format_restaurant_list(restaurants)

        response = f"{header}\n\n{body}"

        # 如果放宽了条件，添加提示
        if result.get("relaxed"):
            response = f"提示: {result['relaxed']}\n\n{response}"

        return response

    def _build_header(self, params: dict, count: int) -> str:
        """构建响应头"""
        conditions = []
        if params.get("taste"):
            conditions.append(f"口味:{params['taste']}")
        if params.get("budget_max"):
            conditions.append(f"预算:{params['budget_max']}元内")
        cuisine = params.get("cuisine") or params.get("category")
        if cuisine:
            conditions.append(f"菜系:{cuisine}")

        if conditions:
            return f"为您找到 {count} 家餐厅 ({', '.join(conditions)})"
        return f"为您找到 {count} 家餐厅"

    async def search(self, params: dict) -> str:
        """
        搜索餐厅

        params:
        - keyword: 搜索关键词（必填）
        - city: 城市
        - location: 坐标（可选，有则搜附近）
        """
        keyword = params.get("keyword")
        if not keyword:
            return "请提供搜索关键词"

        city = params.get("city", self.default_city)
        location = params.get("location")

        # 如果有坐标，使用周边搜索
        if location and location != "unknown":
            result = await self.api.search_nearby(
                location=location,
                query=keyword,
                radius=3000
            )
        else:
            result = await self.api.search_by_keyword(
                keywords=keyword,
                city=city
            )

        restaurants = result.get("restaurants", [])

        if not restaurants:
            return f"未找到与「{keyword}」相关的餐厅，请尝试其他关键词。"

        if location and location != "unknown":
            header = f"在您附近搜索「{keyword}」找到 {len(restaurants)} 家餐厅"
        else:
            header = f"在{city}搜索「{keyword}」找到 {len(restaurants)} 家餐厅"

        body = self._format_restaurant_list(restaurants)
        return f"{header}\n\n{body}"

    async def detail(self, params: dict) -> str:
        """
        获取餐厅详情

        params:
        - restaurant_name: 餐厅名称
        - restaurant_id: POI ID（可选，优先使用）
        - city: 城市
        """
        restaurant_id = params.get("restaurant_id")
        restaurant_name = params.get("restaurant_name")
        city = params.get("city", self.default_city)

        # 如果有ID直接查详情
        if restaurant_id:
            result = await self.api.get_restaurant_detail(restaurant_id)
            if "error" not in result:
                return self._format_detail(result)

        # 否则先搜索再取第一个
        if restaurant_name:
            result = await self.api.search_by_keyword(
                keywords=restaurant_name,
                city=city
            )
            restaurants = result.get("restaurants", [])
            if restaurants:
                return self._format_detail(restaurants[0])

        return "未找到该餐厅信息，请检查餐厅名称是否正确。"

    def _no_result_message(self, taste=None, budget=None, cuisine=None) -> str:
        """无结果时的提示信息"""
        conditions = []
        if taste:
            conditions.append(f"口味:{taste}")
        if budget:
            conditions.append(f"预算:{budget}元内")
        if cuisine:
            conditions.append(f"菜系:{cuisine}")

        msg = "未找到符合条件的餐厅"
        if conditions:
            msg += f" ({', '.join(conditions)})"
        msg += "，建议放宽条件重试。"
        return msg


# ==================== A2A Agent ====================

class FoodDeliveryAgent:
    """外卖助手A2A Agent"""

    def __init__(self):
        self.skills = FoodAgentSkills()
        self.tasks = {}

        # 精简为3个核心技能
        self.skill_handlers = {
            "recommend": self.skills.recommend,
            "search": self.skills.search,
            "detail": self.skills.detail,
        }

    def load_agent_card(self) -> dict:
        import os
        card_path = os.path.join(os.path.dirname(__file__), "agent_card.json")
        with open(card_path, "r", encoding="utf-8") as f:
            return json.load(f)

    async def process_task(self, task_id: str, skill_id: str, params: dict) -> dict:
        """处理任务"""
        handler = self.skill_handlers.get(skill_id)

        if not handler:
            result_text = f"未知的技能: {skill_id}。可用技能: {list(self.skill_handlers.keys())}"
        else:
            try:
                result_text = await handler(params)
            except Exception as e:
                result_text = f"执行出错: {str(e)}"

        task = {
            "id": task_id,
            "status": {
                "state": "completed",
                "timestamp": datetime.now().isoformat()
            },
            "result": {
                "type": "text",
                "text": result_text
            }
        }
        self.tasks[task_id] = task
        return task


# ==================== FastAPI ====================

agent = FoodDeliveryAgent()


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("=" * 50)
    print("外卖助手Agent 启动 (百度地图版)")
    print(f"Agent Card: http://localhost:{config.AGENT_PORT}/.well-known/agent-card.json")
    print(f"A2A Endpoint: http://localhost:{config.AGENT_PORT}/a2a")
    print("Skills: recommend, search, detail")
    print("=" * 50)
    yield
    print("外卖助手Agent 关闭")


app = FastAPI(
    title="Food Delivery Assistant Agent",
    lifespan=lifespan
)


@app.get("/.well-known/agent-card.json")
async def get_agent_card():
    """返回Agent Card"""
    return JSONResponse(content=agent.load_agent_card())


@app.post("/a2a")
async def handle_a2a(request: Request):
    """
    处理A2A JSON-RPC请求

    请求格式:
    {
        "jsonrpc": "2.0",
        "id": "request-id",
        "method": "tasks/send",
        "params": {
            "id": "task-id",
            "skill_id": "recommend",
            "params": {
                "taste": "辣",
                "budget_max": 80,
                "cuisine": "川菜"
            }
        }
    }
    """
    body = await request.json()

    method = body.get("method")
    req_params = body.get("params", {})
    request_id = body.get("id")

    response = {
        "jsonrpc": "2.0",
        "id": request_id
    }

    try:
        if method == "tasks/send":
            task_id = req_params.get("id", str(uuid.uuid4()))
            skill_id = req_params.get("skill_id")
            skill_params = req_params.get("params", {})

            if not skill_id:
                response["error"] = {
                    "code": -32602,
                    "message": "缺少skill_id参数"
                }
            else:
                result = await agent.process_task(task_id, skill_id, skill_params)
                response["result"] = result

        elif method == "tasks/get":
            task_id = req_params.get("id")
            if task_id in agent.tasks:
                response["result"] = agent.tasks[task_id]
            else:
                response["error"] = {"code": -32001, "message": "Task not found"}

        elif method == "agent/info":
            response["result"] = agent.load_agent_card()

        else:
            response["error"] = {"code": -32601, "message": f"Unknown method: {method}"}

    except Exception as e:
        response["error"] = {"code": -32000, "message": str(e)}

    return JSONResponse(content=response)


@app.get("/health")
async def health():
    return {"status": "ok", "api": "baidu"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=config.AGENT_HOST, port=config.AGENT_PORT)
