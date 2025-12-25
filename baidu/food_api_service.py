"""
餐厅API服务模块 - 使用百度地图POI搜索API
百度地图Web服务API文档: https://lbsyun.baidu.com/faq/api?title=webapi/guide/webservice-placeapi
"""

import httpx
from typing import Optional, Tuple
from config import config


class FoodAPIService:
    """餐厅数据服务 - 基于百度地图Place API"""

    def __init__(self):
        self.ak = config.BAIDU_MAP_AK
        self.base_url = "https://api.map.baidu.com"

    def swap_coord_order(self, amap_location: str) -> str:
        """
        交换坐标顺序：高德(经度,纬度) -> 百度(纬度,经度)
        坐标系转换由百度API的coord_type=2参数自动处理
        """
        try:
            parts = amap_location.split(",")
            if len(parts) == 2:
                return f"{parts[1]},{parts[0]}"  # 交换顺序
        except Exception:
            pass
        return amap_location

    async def geocode(self, address: str, city: str = "") -> Optional[str]:
        """
        地理编码：地址 -> 坐标

        Args:
            address: 地址，如"新街口"、"南京大学"
            city: 城市，提高精度

        Returns:
            坐标字符串 "纬度,经度" (百度格式)，失败返回None
        """
        params = {
            "ak": self.ak,
            "address": address,
            "output": "json",
        }
        if city:
            params["city"] = city

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.base_url}/geocoding/v3/",
                    params=params,
                    timeout=10.0
                )
                data = response.json()

                if data.get("status") == 0 and data.get("result"):
                    loc = data["result"]["location"]
                    return f"{loc['lat']},{loc['lng']}"
            except Exception as e:
                print(f"地理编码失败: {e}")

        return None

    async def search_nearby(
        self,
        location: str,
        query: Optional[str] = None,
        tag: Optional[str] = None,
        radius: int = 3000,
        page: int = 0,
        page_size: int = 20
    ) -> dict:
        """
        周边搜索餐厅 (百度地图API)

        Args:
            location: 中心点坐标，格式：经度,纬度 (高德格式)
            query: 搜索关键词
            tag: 分类标签
            radius: 搜索半径(米)，最大50000
            page: 页码，从0开始
            page_size: 每页数量，最大20

        Returns:
            搜索结果
        """
        # 交换坐标顺序：高德(经度,纬度) -> 百度(纬度,经度)
        baidu_location = self.swap_coord_order(location)

        params = {
            "ak": self.ak,
            "location": baidu_location,
            "radius": min(radius, 50000),
            "scope": 2,  # 返回详细信息
            "output": "json",
            "page_num": page,
            "page_size": min(page_size, 20),
            "coord_type": 2,  # GCJ-02坐标，百度自动转换
        }

        # 设置搜索关键词
        if query:
            params["query"] = query
        else:
            params["query"] = "美食"

        if tag:
            params["tag"] = tag

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.base_url}/place/v2/search",
                    params=params,
                    timeout=10.0
                )
                data = response.json()

                if data.get("status") == 0:
                    return self._parse_poi_results(data.get("results", []))
                else:
                    return {"error": data.get("message", "搜索失败"), "restaurants": []}

            except Exception as e:
                return {"error": str(e), "restaurants": []}

    async def search_by_keyword(
        self,
        keywords: str,
        city: str = "北京",
        tag: Optional[str] = None,
        page: int = 0,
        page_size: int = 20
    ) -> dict:
        """
        关键词搜索餐厅 (百度地图API)

        Args:
            keywords: 搜索关键词
            city: 城市名称
            tag: 分类标签
            page: 页码
            page_size: 每页数量

        Returns:
            搜索结果
        """
        params = {
            "ak": self.ak,
            "query": keywords,
            "region": city,
            "city_limit": "true",
            "scope": 2,
            "output": "json",
            "page_num": page,
            "page_size": min(page_size, 20),
        }

        if tag:
            params["tag"] = tag

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.base_url}/place/v2/search",
                    params=params,
                    timeout=10.0
                )
                data = response.json()

                if data.get("status") == 0:
                    return self._parse_poi_results(data.get("results", []))
                else:
                    return {"error": data.get("message", "搜索失败"), "restaurants": []}

            except Exception as e:
                return {"error": str(e), "restaurants": []}

    async def get_restaurant_detail(self, uid: str) -> dict:
        """
        获取餐厅详情 (百度地图API)

        Args:
            uid: POI的唯一标识

        Returns:
            餐厅详细信息
        """
        params = {
            "ak": self.ak,
            "uid": uid,
            "scope": 2,
            "output": "json",
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.base_url}/place/v2/detail",
                    params=params,
                    timeout=10.0
                )
                data = response.json()

                if data.get("status") == 0 and data.get("result"):
                    return self._parse_single_poi(data["result"])
                else:
                    return {"error": "未找到餐厅信息"}

            except Exception as e:
                return {"error": str(e)}

    def _parse_poi_results(self, results: list) -> dict:
        """解析POI搜索结果"""
        restaurants = []
        for poi in results:
            restaurants.append(self._parse_single_poi(poi))
        return {"restaurants": restaurants, "count": len(restaurants)}

    def _parse_single_poi(self, poi: dict) -> dict:
        """
        解析单个POI数据 (百度地图API格式)

        百度地图返回的字段:
        - name: 名称
        - location: {lat, lng}
        - address: 地址
        - telephone: 电话
        - detail_info: {
            tag: 标签
            overall_rating: 总体评分
            price: 人均价格
            shop_hours: 营业时间
            ...
        }
        """
        detail = poi.get("detail_info", {})

        # 评分
        rating = detail.get("overall_rating", "")
        if not rating:
            rating = "暂无"

        # 人均消费
        price = detail.get("price", "")
        if not price:
            price = "暂无"

        # 电话
        tel = poi.get("telephone", "") or "暂无"

        # 营业时间
        shop_hours = detail.get("shop_hours", "") or "暂无"

        # 标签
        tag = detail.get("tag", "")

        # 解析距离 (百度返回的是米数)
        distance = detail.get("distance", "")
        if distance:
            distance = f"{distance}m"

        # 位置
        location = poi.get("location", {})
        location_str = f"{location.get('lng', '')},{location.get('lat', '')}" if location else ""

        return {
            "id": poi.get("uid", ""),
            "name": poi.get("name", "未知"),
            "type": tag.split(";")[0] if tag else "餐厅",
            "address": poi.get("address", "暂无地址"),
            "location": location_str,
            "tel": tel,
            "rating": rating,
            "cost": price,
            "distance": distance,
            "business_hours": shop_hours,
            "tag": tag,
            "city": poi.get("city", ""),
            "area": poi.get("area", ""),
        }

    def _filter_by_budget(self, restaurants: list, budget_max: int) -> list:
        """
        按预算严格过滤餐厅（不包含价格未知的）
        """
        filtered = []
        for r in restaurants:
            price = r.get("cost")
            if price and price != "暂无":
                try:
                    price_num = int(float(str(price).replace("元", "").strip()))
                    if price_num <= budget_max:
                        filtered.append(r)
                except (ValueError, TypeError):
                    pass  # 解析失败的不包含
        return filtered

    async def unified_search(
        self,
        query: str,
        location: Optional[str] = None,
        location_name: Optional[str] = None,
        city: str = "北京",
        budget_max: Optional[int] = None,
        delivery_only: bool = False,
        radius: int = 3000
    ) -> dict:
        """
        统一搜索接口

        Args:
            query: 搜索关键词（菜系、餐厅名等）
            location: 坐标，高德格式"经度,纬度"
            location_name: 地点名称（如"新街口"），会自动转坐标
            city: 城市
            budget_max: 预算上限（严格筛选，不自动放宽）
            delivery_only: 是否只看外卖
            radius: 搜索半径（米）

        Returns:
            {
                "restaurants": [...],
                "count": int,
                "search_info": "搜索信息描述"
            }
        """
        search_info_parts = []

        # 1. 确定搜索坐标
        final_location = None

        # 优先使用地点名称解析坐标
        if location_name:
            geocoded = await self.geocode(location_name, city)
            if geocoded:
                # geocode返回的已经是百度格式(纬度,经度)，需要转回高德格式给search_nearby处理
                parts = geocoded.split(",")
                final_location = f"{parts[1]},{parts[0]}"  # 转为经度,纬度
                search_info_parts.append(f"在「{location_name}」附近")
            else:
                search_info_parts.append(f"无法解析「{location_name}」，使用城市搜索")

        # 其次使用传入的坐标（高德格式：经度,纬度）
        if not final_location and location and location != "unknown":
            final_location = location  # 直接传给search_nearby，由它来转换
            search_info_parts.append("在当前位置附近")

        # 2. 构建搜索关键词
        search_query = query
        if delivery_only:
            search_query = f"{query} 外卖"
            search_info_parts.append("只看外卖")

        # 3. 执行搜索
        if final_location:
            result = await self.search_nearby(
                location=final_location,
                query=search_query,
                radius=radius
            )
        else:
            result = await self.search_by_keyword(
                keywords=search_query,
                city=city
            )
            search_info_parts.append(f"在{city}搜索")

        restaurants = result.get("restaurants", [])

        # 4. 预算筛选（严格，不自动放宽）
        if budget_max and restaurants:
            original_count = len(restaurants)
            restaurants = self._filter_by_budget(restaurants, budget_max)
            if len(restaurants) < original_count:
                search_info_parts.append(f"人均{budget_max}元内")
                if not restaurants:
                    search_info_parts.append("（无符合预算的结果）")

        # 5. 构建返回结果
        search_info = "，".join(search_info_parts) if search_info_parts else f"搜索「{query}」"

        return {
            "restaurants": restaurants,
            "count": len(restaurants),
            "query": query,
            "search_info": search_info
        }


# 单例
food_api_service = FoodAPIService()
