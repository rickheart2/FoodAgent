"""
餐厅API服务模块 - 使用高德地图POI搜索API v5
高德地图Web服务API文档: https://lbs.amap.com/api/webservice/guide/api/newpoisearch
"""

import httpx
from typing import Optional
from config import config


class FoodAPIService:
    """餐厅数据服务 - 基于高德地图POI API v5"""

    def __init__(self):
        self.api_key = config.AMAP_API_KEY
        self.base_url = "https://restapi.amap.com/v5/place"

        # 口味→关键词映射
        self.taste_keywords = {
            "清淡": ["粤菜", "日料", "素食"],
            "辣": ["川菜", "湘菜", "火锅"],
            "鲜": ["海鲜", "日料", "粤菜"],
        }

    async def search_nearby(
        self,
        location: str,
        keywords: Optional[str] = None,
        radius: int = 3000,
        page: int = 1,
        page_size: int = 20
    ) -> dict:
        """
        周边搜索餐厅 (高德地图API v5)

        Args:
            location: 中心点坐标，格式：经度,纬度
            keywords: 搜索关键词
            radius: 搜索半径(米)
            page: 页码，从1开始
            page_size: 每页数量

        Returns:
            搜索结果
        """
        params = {
            "key": self.api_key,
            "location": location,
            "radius": radius,
            "types": "050000",  # 餐饮服务大类
            "page_num": page,
            "page_size": min(page_size, 25),
            "show_fields": "business",
        }

        if keywords:
            params["keywords"] = keywords

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.base_url}/around",
                    params=params,
                    timeout=10.0
                )
                data = response.json()

                if data.get("status") == "1":
                    return self._parse_poi_results(data.get("pois", []))
                else:
                    return {"error": data.get("info", "搜索失败"), "restaurants": []}

            except Exception as e:
                return {"error": str(e), "restaurants": []}

    async def search_by_keyword(
        self,
        keywords: str,
        city: str = "北京",
        page: int = 1,
        page_size: int = 20
    ) -> dict:
        """
        关键词搜索餐厅 (高德地图API v5)

        Args:
            keywords: 搜索关键词
            city: 城市名称
            page: 页码
            page_size: 每页数量

        Returns:
            搜索结果
        """
        params = {
            "key": self.api_key,
            "keywords": keywords,
            "city": city,
            "citylimit": "true",
            "types": "050000",  # 餐饮服务大类
            "page_num": page,
            "page_size": min(page_size, 25),
            "show_fields": "business",
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.base_url}/text",
                    params=params,
                    timeout=10.0
                )
                data = response.json()

                if data.get("status") == "1":
                    return self._parse_poi_results(data.get("pois", []))
                else:
                    return {"error": data.get("info", "搜索失败"), "restaurants": []}

            except Exception as e:
                return {"error": str(e), "restaurants": []}

    async def get_restaurant_detail(self, poi_id: str) -> dict:
        """
        获取餐厅详情 (高德地图API v5)

        Args:
            poi_id: POI的唯一标识

        Returns:
            餐厅详细信息
        """
        params = {
            "key": self.api_key,
            "id": poi_id,
            "show_fields": "business",
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.base_url}/detail",
                    params=params,
                    timeout=10.0
                )
                data = response.json()

                if data.get("status") == "1" and data.get("pois"):
                    return self._parse_single_poi(data["pois"][0])
                else:
                    return {"error": "未找到餐厅信息"}

            except Exception as e:
                return {"error": str(e)}

    def _parse_poi_results(self, pois: list) -> dict:
        """解析POI搜索结果"""
        restaurants = []
        for poi in pois:
            restaurants.append(self._parse_single_poi(poi))
        return {"restaurants": restaurants, "count": len(restaurants)}

    def _parse_single_poi(self, poi: dict) -> dict:
        """
        解析单个POI数据 (高德地图API v5格式)

        高德v5返回的business字段:
        - tel: 电话
        - business_area: 商圈
        - rating: 评分
        - cost: 人均消费
        - tag: 特色标签
        - opentime_today: 今日营业时间
        - keytag: 关键标签
        """
        business = poi.get("business", {})

        # 评分
        rating = business.get("rating", "") or "暂无"

        # 人均消费
        cost = business.get("cost", "") or "暂无"

        # 电话
        tel = business.get("tel", "") or "暂无"

        # 营业时间
        opentime = business.get("opentime_today", "") or "暂无"

        # 标签
        tag = business.get("tag", "") or ""
        keytag = business.get("keytag", "") or ""

        # 距离
        distance = poi.get("distance", "")
        if distance:
            distance = f"{distance}m"

        return {
            "id": poi.get("id", ""),
            "name": poi.get("name", "未知"),
            "type": poi.get("type", "").split(";")[0] if poi.get("type") else "餐厅",
            "address": poi.get("address", "暂无地址"),
            "location": poi.get("location", ""),
            "tel": tel,
            "rating": rating,
            "cost": cost,
            "distance": distance,
            "business_hours": opentime,
            "tag": tag or keytag,
            "city": poi.get("cityname", ""),
            "area": poi.get("adname", ""),
        }

    def get_cuisines_by_taste(self, taste: str) -> list:
        """根据口味获取推荐关键词"""
        return self.taste_keywords.get(taste, [])

    async def geocode(self, address: str, city: str = None) -> Optional[str]:
        """
        地理编码 - 将地址转换为坐标

        Args:
            address: 地址字符串
            city: 城市名称

        Returns:
            坐标字符串 "经度,纬度"，失败返回None
        """
        params = {
            "key": self.api_key,
            "address": address,
        }
        if city:
            params["city"] = city

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    "https://restapi.amap.com/v3/geocode/geo",
                    params=params,
                    timeout=10.0
                )
                data = response.json()

                if data.get("status") == "1" and data.get("geocodes"):
                    return data["geocodes"][0].get("location")
                return None

            except Exception:
                return None

    async def ip_locate(self, ip: str = None) -> dict:
        """
        IP定位 - 根据IP地址获取位置信息

        Args:
            ip: IP地址，不传则使用请求方IP

        Returns:
            {
                "location": "经度,纬度" 或 None,
                "city": "城市名称",
                "province": "省份"
            }
        """
        params = {"key": self.api_key}
        if ip:
            params["ip"] = ip

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    "https://restapi.amap.com/v3/ip",
                    params=params,
                    timeout=10.0
                )
                data = response.json()

                if data.get("status") == "1":
                    # 高德IP定位可能只返回城市级别，没有精确坐标
                    rectangle = data.get("rectangle", "")
                    location = None
                    if rectangle:
                        # rectangle格式: "经度1,纬度1;经度2,纬度2"
                        coords = rectangle.split(";")[0]
                        location = coords

                    return {
                        "location": location,
                        "city": data.get("city", ""),
                        "province": data.get("province", ""),
                    }

                return {"error": data.get("info", "IP定位失败")}

            except Exception as e:
                return {"error": str(e)}

    async def resolve_location(
        self,
        location: str = None,
        address: str = None,
        city: str = None,
        ip: str = None
    ) -> tuple[str, str]:
        """
        解析位置 - 优先使用坐标，其次解析地址，最后IP定位

        Returns:
            (坐标字符串, 城市名称)
            - 有精确位置时返回 ("116.xx,39.xx", "北京")
            - 仅有城市级别时返回 ("unknown", "北京")
        """
        default_city = "北京"

        # 已有坐标
        if location and "," in location and location != "unknown":
            return location, city or default_city

        # 解析地址
        if address:
            resolved = await self.geocode(address, city)
            if resolved:
                return resolved, city or default_city

        # IP定位
        ip_result = await self.ip_locate(ip)

        if ip_result.get("city"):
            location = ip_result.get("location")
            if location:
                return location, ip_result["city"]
            return "unknown", ip_result["city"]

        if city:
            return "unknown", city

        return "unknown", default_city

    def _filter_by_budget(self, restaurants: list, budget_max: int, include_unknown: bool = True) -> list:
        """按预算过滤餐厅"""
        filtered = []
        for r in restaurants:
            price = r.get("cost")
            if price and price != "暂无":
                try:
                    price_num = int(float(str(price).replace("元", "").strip()))
                    if price_num <= budget_max:
                        filtered.append(r)
                except (ValueError, TypeError):
                    if include_unknown:
                        filtered.append(r)
            else:
                if include_unknown:
                    filtered.append(r)
        return filtered

    async def _do_search(self, location: str, keywords: Optional[str], city: str) -> dict:
        """执行搜索"""
        if location and location != "unknown":
            return await self.search_nearby(location=location, keywords=keywords)
        else:
            return await self.search_by_keyword(keywords=keywords or "美食", city=city)

    async def smart_search(
        self,
        location: str,
        taste: Optional[str] = None,
        cuisine: Optional[str] = None,
        budget_max: Optional[int] = None,
        keywords: Optional[str] = None,
        city: str = "北京"
    ) -> dict:
        """
        智能搜索 - 综合多个条件搜索餐厅
        简化版：直接用关键词搜索，按预算过滤，不做复杂fallback
        """
        # 确定搜索关键词
        final_keywords = cuisine or keywords
        if not final_keywords and taste:
            cuisines = self.get_cuisines_by_taste(taste)
            if cuisines:
                final_keywords = cuisines[0]

        if not final_keywords:
            final_keywords = "美食"

        # 执行搜索
        result = await self._do_search(location, final_keywords, city)
        restaurants = result.get("restaurants", [])

        if not restaurants:
            return result

        # 如果有预算限制，过滤
        if budget_max:
            filtered = self._filter_by_budget(restaurants, budget_max, include_unknown=True)
            if filtered:
                result["restaurants"] = filtered
                result["count"] = len(filtered)

        return result


# 单例
food_api_service = FoodAPIService()
