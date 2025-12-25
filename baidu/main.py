"""
外卖/美食助手 A2A Agent - 简化版
统一搜索接口，支持地点名、预算筛选、外卖筛选
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
    """美食Agent技能 - 统一搜索接口"""

    def __init__(self):
        self.api = food_api_service
        self.default_city = "南京"

    def _format_restaurant(self, r: dict, index: int = None) -> str:
        """格式化单个餐厅信息"""
        prefix = f"{index}. " if index else ""
        lines = [f"**{prefix}{r.get('name', '未知')}**"]

        # 基本信息
        info_parts = []
        if r.get('type') and r.get('type') != '餐厅':
            info_parts.append(r.get('type'))
        if r.get('rating') and r.get('rating') != '暂无':
            info_parts.append(f"评分:{r.get('rating')}")
        if r.get('cost') and r.get('cost') != '暂无':
            info_parts.append(f"人均:{r.get('cost')}元")
        if r.get('distance'):
            info_parts.append(r.get('distance'))

        if info_parts:
            lines.append(f"   {' | '.join(info_parts)}")

        lines.append(f"   {r.get('address', '暂无地址')}")

        if r.get('tel') and r.get('tel') != '暂无':
            lines.append(f"   电话: {r.get('tel')}")

        return "\n".join(lines)

    def _format_restaurant_list(self, restaurants: list, limit: int = 10) -> str:
        """格式化餐厅列表"""
        result = []
        for i, r in enumerate(restaurants[:limit], 1):
            result.append(self._format_restaurant(r, i))
        return "\n\n".join(result)

    async def search(self, params: dict) -> str:
        """
        统一搜索接口

        params:
        - query: 搜索关键词（菜系、餐厅名等）【必填】
        - location: 坐标，高德格式"经度,纬度"
        - location_name: 地点名称（如"新街口"），会自动转坐标
        - city: 城市
        - budget_max: 预算上限（严格筛选）
        - delivery_only: 是否只看外卖（true/false）
        """
        query = params.get("query") or params.get("keyword") or params.get("cuisine")
        if not query:
            return "请输入搜索内容（如：火锅、海底捞、日料...）"

        # 调用统一搜索
        result = await self.api.unified_search(
            query=query,
            location=params.get("location"),
            location_name=params.get("location_name"),
            city=params.get("city", self.default_city),
            budget_max=int(params["budget_max"]) if params.get("budget_max") else None,
            delivery_only=bool(params.get("delivery_only")),
            radius=int(params.get("radius", 3000))
        )

        restaurants = result.get("restaurants", [])
        search_info = result.get("search_info", "")

        if not restaurants:
            return f"未找到结果（{search_info}）\n\n建议：\n- 尝试其他关键词\n- 放宽预算限制\n- 扩大搜索范围"

        header = f"搜索「{query}」找到 {len(restaurants)} 家餐厅"
        if search_info:
            header = f"{search_info}\n{header}"

        body = self._format_restaurant_list(restaurants)
        return f"{header}\n\n{body}"


# ==================== A2A Agent ====================

class FoodDeliveryAgent:
    """外卖助手A2A Agent"""

    def __init__(self):
        self.skills = FoodAgentSkills()
        self.tasks = {}

        # 简化为单一搜索技能
        self.skill_handlers = {
            "search": self.skills.search,
            # 兼容旧接口
            "recommend": self.skills.search,
            "detail": self.skills.search,
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
            return {
                "id": task_id,
                "status": "failed",
                "error": f"未知技能: {skill_id}，支持的技能: search"
            }

        try:
            result = await handler(params)
            self.tasks[task_id] = {
                "id": task_id,
                "status": "completed",
                "result": {"type": "text", "text": result},
                "completed_at": datetime.now().isoformat()
            }
            return self.tasks[task_id]

        except Exception as e:
            self.tasks[task_id] = {
                "id": task_id,
                "status": "failed",
                "error": str(e)
            }
            return self.tasks[task_id]


# ==================== FastAPI ====================

agent = FoodDeliveryAgent()


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("=" * 50)
    print("美食助手Agent 启动 (百度地图版 v3.0)")
    print(f"API: http://localhost:{config.AGENT_PORT}/a2a")
    print("功能: 统一搜索（支持地点名、预算、外卖筛选）")
    print("=" * 50)
    yield
    print("美食助手Agent 关闭")


app = FastAPI(title="美食助手Agent", lifespan=lifespan)


@app.get("/.well-known/agent-card.json")
async def get_agent_card():
    return agent.load_agent_card()


@app.post("/a2a")
async def handle_a2a(request: Request):
    """处理A2A JSON-RPC请求"""
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
    return {"status": "ok", "api": "baidu", "version": "3.0"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=config.AGENT_HOST, port=config.AGENT_PORT)
