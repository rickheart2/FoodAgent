"""
餐厅API服务模块 - 使用百度地图POI搜索API
百度地图Web服务API文档: https://lbsyun.baidu.com/faq/api?title=webapi/guide/webservice-placeapi
"""

import httpx
from typing import Optional
from config import config


class FoodAPIService:
    """餐厅数据服务 - 基于百度地图Place API"""

    def __init__(self):
        self.ak = config.BAIDU_MAP_AK
        self.base_url = "https://api.map.baidu.com"

        # 美食分类标签
        self.food_types = {
            "中餐": "中餐厅",
            "川菜": "川菜",
            "粤菜": "粤菜",
            "湘菜": "湘菜",
            "东北菜": "东北菜",
            "火锅": "火锅",
            "海鲜": "海鲜",
            "西餐": "西餐",
            "日料": "日本料理",
            "韩餐": "韩国料理",
            "快餐": "快餐",
            "咖啡厅": "咖啡厅",
            "茶馆": "茶馆",
            "甜点": "甜品店",
            "小吃": "小吃",
            "烧烤": "烧烤",
        }

        # 口味关键词映射
        self.taste_keywords = {
            "清淡": ["粤菜", "日本料理", "素食"],
            "辣": ["川菜", "湘菜", "火锅"],
            "鲜": ["海鲜", "日本料理", "粤菜"],
        }

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

    def get_tag(self, cuisine: str) -> Optional[str]:
        """根据菜系名称获取百度地图标签"""
        return self.food_types.get(cuisine)

    def get_cuisines_by_taste(self, taste: str) -> list:
        """根据口味获取推荐菜系"""
        return self.taste_keywords.get(taste, [])

    async def geocode(self, address: str, city: str = None) -> Optional[str]:
        """
        地理编码 - 将地址转换为坐标

        Args:
            address: 地址字符串
            city: 城市名称

        Returns:
            坐标字符串 "纬度,经度"（百度格式），失败返回None
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
                    location = data["result"].get("location", {})
                    lat = location.get("lat")
                    lng = location.get("lng")
                    if lat and lng:
                        return f"{lat},{lng}"
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
                "location": "纬度,经度" 或 None,
                "city": "城市名称",
                "province": "省份"
            }
        """
        params = {
            "ak": self.ak,
            "coor": "bd09ll",
        }
        if ip:
            params["ip"] = ip

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.base_url}/location/ip",
                    params=params,
                    timeout=10.0
                )
                data = response.json()

                if data.get("status") == 0:
                    content = data.get("content", {})
                    address_detail = content.get("address_detail", {})
                    point = content.get("point", {})

                    location = None
                    if point.get("x") and point.get("y"):
                        location = f"{point['y']},{point['x']}"

                    return {
                        "location": location,
                        "city": address_detail.get("city", ""),
                        "province": address_detail.get("province", ""),
                    }

                return {"error": data.get("message", "IP定位失败")}

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
            - 有精确位置时返回 ("39.xx,116.xx", "北京")
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

    async def _do_search(self, location: str, query: Optional[str], city: str) -> dict:
        """执行搜索"""
        if location and location != "unknown":
            return await self.search_nearby(location=location, query=query)
        else:
            return await self.search_by_keyword(keywords=query or "美食", city=city)

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

        关键词策略（优先级）：
        1. 用户指定的 cuisine（如"川菜"）
        2. 用户指定的 keywords
        3. 根据 taste 推断的菜系（分别搜索后合并）

        自动放宽条件策略：
        1. 严格匹配：预算内 + 排除价格未知
        2. 放宽预算：预算 * 1.5
        3. 包含未知：包含价格未知的餐厅
        4. 扩大范围：去掉口味/菜系限制
        """
        # 关键词策略
        final_query = None

        if cuisine:
            final_query = self.get_tag(cuisine) or cuisine
        elif keywords:
            final_query = keywords
        elif taste:
            cuisines = self.get_cuisines_by_taste(taste)
            if cuisines:
                final_query = cuisines[0]

        # 执行搜索
        result = await self._do_search(location, final_query, city)

        # 如果有口味偏好但搜索结果少，尝试搜索其他相关菜系并合并
        if taste and not cuisine and result.get("restaurants"):
            cuisines = self.get_cuisines_by_taste(taste)
            if len(cuisines) > 1 and len(result.get("restaurants", [])) < 10:
                existing_ids = {r["id"] for r in result["restaurants"]}
                for other_cuisine in cuisines[1:]:
                    other_result = await self._do_search(location, other_cuisine, city)
                    for r in other_result.get("restaurants", []):
                        if r["id"] not in existing_ids:
                            result["restaurants"].append(r)
                            existing_ids.add(r["id"])
                result["count"] = len(result["restaurants"])

        # 如果搜索本身无结果，尝试扩大范围
        if not result.get("restaurants") and final_query:
            broader_result = await self._do_search(location, "美食", city)
            if broader_result.get("restaurants"):
                broader_result["relaxed"] = "已扩大搜索范围（放宽口味/菜系限制）"
                result = broader_result

        if not result.get("restaurants"):
            return result

        # 如果没有预算限制，直接返回
        if not budget_max:
            return result

        all_restaurants = result["restaurants"]
        existing_relaxed = result.get("relaxed")

        # 策略1: 严格匹配
        filtered = self._filter_by_budget(all_restaurants, budget_max, include_unknown=False)
        if filtered:
            result["restaurants"] = filtered
            result["count"] = len(filtered)
            return result

        # 策略2: 放宽预算
        relaxed_budget = int(budget_max * 1.5)
        filtered = self._filter_by_budget(all_restaurants, relaxed_budget, include_unknown=False)
        if filtered:
            result["restaurants"] = filtered
            result["count"] = len(filtered)
            relaxed_msg = f"已放宽预算至{relaxed_budget}元"
            result["relaxed"] = f"{existing_relaxed}，{relaxed_msg}" if existing_relaxed else relaxed_msg
            return result

        # 策略3: 包含价格未知
        filtered = self._filter_by_budget(all_restaurants, budget_max, include_unknown=True)
        if filtered:
            result["restaurants"] = filtered
            result["count"] = len(filtered)
            relaxed_msg = "包含了部分价格未知的餐厅"
            result["relaxed"] = f"{existing_relaxed}，{relaxed_msg}" if existing_relaxed else relaxed_msg
            return result

        # 策略4: 扩大搜索范围
        if final_query:
            broader_result = await self._do_search(location, "美食", city)
            if broader_result.get("restaurants"):
                filtered = self._filter_by_budget(broader_result["restaurants"], budget_max, include_unknown=True)
                if filtered:
                    broader_result["restaurants"] = filtered
                    broader_result["count"] = len(filtered)
                    broader_result["relaxed"] = "已扩大搜索范围（去除口味/菜系限制）"
                    return broader_result

        # 所有策略都失败，返回原始结果
        result["restaurants"] = all_restaurants[:5]
        result["count"] = len(result["restaurants"])
        relaxed_msg = "未找到符合预算的餐厅，以下为附近热门餐厅参考"
        result["relaxed"] = f"{existing_relaxed}，{relaxed_msg}" if existing_relaxed else relaxed_msg
        return result


# 单例
food_api_service = FoodAPIService()
