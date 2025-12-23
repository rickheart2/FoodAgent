# 外卖/美食助手 A2A Agent

基于 [A2A协议](https://github.com/google/A2A) 的智能外卖推荐Agent，集成阿里云Qwen大模型 + 高德地图真实餐厅数据。

## 项目架构

```
┌─────────────────┐      ┌──────────────────────────────────────┐
│   主控 Agent    │      │         Food Delivery Agent          │
│                 │      │                                      │
│  理解用户意图   │ ──── │  /.well-known/agent-card.json       │
│  选择skill      │ POST │  /a2a  (JSON-RPC)                   │
│  构造参数       │ ───► │                                      │
│                 │      │  ┌─────────┐  ┌─────────┐           │
│                 │ ◄─── │  │ 高德API │  │  Qwen   │           │
│   展示结果      │      │  │ 真实数据 │  │ 组织语言 │           │
└─────────────────┘      │  └─────────┘  └─────────┘           │
                         └──────────────────────────────────────┘
```

## 目录结构

```
food_agent/
├── main.py              # 主程序入口，A2A服务 + Skill实现
├── config.py            # 配置管理，加载环境变量
├── llm_service.py       # Qwen大模型服务封装
├── food_api_service.py  # 高德地图POI餐厅数据 + 定位服务
├── agent_card.json      # Agent Card定义（skills + inputSchema）
├── requirements.txt     # Python依赖
├── .env                 # 环境变量配置（API密钥）
├── .env.example         # 环境变量示例
├── quick_test.py        # 快速测试脚本
└── poi.txt              # 高德POI分类码参考
```

## 模块说明

### 1. main.py - 主程序

**职责**：启动FastAPI服务，暴露A2A接口，实现各个Skill

```python
# 暴露的端点
GET  /.well-known/agent-card.json  # 返回Agent能力描述
POST /a2a                           # 接收JSON-RPC请求，执行skill
GET  /health                        # 健康检查
```

**Skill列表**：

| Skill ID | 功能 | 必需参数 |
|----------|------|----------|
| `smart_recommend` | 智能推荐 | - |
| `recommend_by_taste` | 按口味推荐 | `taste` |
| `recommend_by_budget` | 按预算推荐 | `budget_max` |
| `search_restaurant` | 搜索餐厅 | `keyword` |
| `browse_category` | 分类浏览 | `category` |
| `get_restaurant_detail` | 餐厅详情 | `restaurant_name` |

### 2. config.py - 配置管理

从 `.env` 文件加载配置：

```python
QWEN_API_KEY      # 阿里云Qwen API密钥
QWEN_MODEL        # 模型名称 (qwen-turbo/qwen-plus/qwen-max)
AMAP_API_KEY      # 高德地图API密钥
AGENT_HOST        # 服务监听地址
AGENT_PORT        # 服务端口
```

### 3. llm_service.py - Qwen服务

封装阿里云DashScope API（OpenAI兼容接口）：

- `chat()` - 基础对话
- `generate_recommendation()` - 生成餐厅推荐文案
- `generate_detail_description()` - 生成餐厅详情描述

### 4. food_api_service.py - 餐厅数据服务

封装高德地图API (v3)：

**POI搜索**：
- `search_nearby()` - 周边搜索（需要精确坐标）
- `search_by_keyword()` - 关键词搜索（城市级别）
- `smart_search()` - 智能搜索（综合口味/预算/菜系）
- `get_restaurant_detail()` - 获取POI详情

**位置服务**：
- `geocode()` - 地理编码（地址 → 坐标）
- `ip_locate()` - IP定位（IP → 城市，基础版仅支持城市级别）
- `resolve_location()` - 智能位置解析

### 5. agent_card.json - Agent Card

定义Agent的能力描述，供主控Agent发现和调用。

---

## Quick Start

### 1. 安装依赖

```bash
cd D:\Project\food_agent
pip install -r requirements.txt
```

### 2. 配置API密钥

编辑 `.env` 文件（或复制 `.env.example`）：

```env
# 阿里云Qwen - 获取地址: https://dashscope.console.aliyun.com/
QWEN_API_KEY=sk-xxxxxxxx

# 高德地图 - 获取地址: https://console.amap.com/dev/key/app
AMAP_API_KEY=xxxxxxxx

# 服务配置
AGENT_HOST=0.0.0.0
AGENT_PORT=8080
```

### 3. 启动服务

```bash
python main.py
```

输出：
```
==================================================
外卖助手Agent 启动
Agent Card: http://localhost:8080/.well-known/agent-card.json
A2A Endpoint: http://localhost:8080/a2a
==================================================
INFO:     Uvicorn running on http://0.0.0.0:8080
```

### 4. 测试

```bash
python quick_test.py
# 结果保存在 test_results.json
```

---

## 位置定位策略

### 搜索策略

根据位置精度自动选择搜索方式：

| 位置精度 | 搜索方式 | 说明 |
|----------|----------|------|
| 精确坐标 (`location`) | 周边搜索 | `search_nearby()` 3km范围内 |
| 详细地址 (`address`) | 周边搜索 | 先地理编码转坐标，再周边搜索 |
| 仅IP/城市 | 城市级关键词搜索 | `search_by_keyword()` 全城搜索 |

### 位置解析优先级

```
1. location（坐标）    → 精确位置，周边搜索
2. address（地址）     → 地理编码转坐标，周边搜索
3. ip / 自动IP定位     → 仅获取城市，城市级关键词搜索
4. city（城市名）      → 城市级关键词搜索
5. 默认（北京）        → 兜底方案
```

### 为什么IP定位只能城市级搜索？

高德基础IP定位API (`/v3/ip`) 仅返回：
- 省份、城市、城市编码
- **不返回**精确坐标或区县

因此当只有IP时，无法做"周边3km"搜索，只能做城市级关键词搜索。

如需精确定位，建议：
1. 主控Agent在客户端获取用户GPS/地址，传入 `location` 或 `address` 参数
2. 或开通高德高级IP定位服务（可精确到区县+坐标）

### 使用示例

**精确位置 - 周边搜索**

```json
{
  "skill_id": "browse_category",
  "params": {
    "category": "火锅",
    "address": "成都市锦江区春熙路",
    "city": "成都"
  }
}
```

**仅城市 - 城市级搜索**

```json
{
  "skill_id": "browse_category",
  "params": {
    "category": "火锅",
    "city": "成都"
  }
}
```

---

## POI分类码

使用高德官方POI分类码（参考 `poi.txt`）：

| 分类 | POI码 | 说明 |
|------|-------|------|
| 中餐 | 050100 | 中餐厅大类 |
| 川菜 | 050102 | 四川菜 |
| 粤菜 | 050103 | 广东菜 |
| 湘菜 | 050108 | 湖南菜 |
| 东北菜 | 050113 | |
| 火锅 | 050117 | 火锅店 |
| 海鲜 | 050119 | 海鲜酒楼 |
| 素食 | 050120 | 中式素菜馆 |
| 西餐 | 050201 | 西餐厅 |
| 日料 | 050202 | 日本料理 |
| 韩餐 | 050203 | 韩国料理 |
| 快餐 | 050300 | 快餐厅 |
| 咖啡厅 | 050500 | |
| 甜点 | 050900 | 甜品店 |

搜索时同时使用 `keywords` 和 `types` 参数提高准确性。

---

## 请求/响应格式

### 请求格式（主控Agent发送）

```json
{
  "jsonrpc": "2.0",
  "id": "request-001",
  "method": "tasks/send",
  "params": {
    "id": "task-001",
    "skill_id": "browse_category",
    "params": {
      "category": "火锅",
      "address": "成都市锦江区春熙路",
      "city": "成都"
    }
  }
}
```

### 响应格式

```json
{
  "jsonrpc": "2.0",
  "id": "request-001",
  "result": {
    "id": "task-001",
    "status": {
      "state": "completed",
      "timestamp": "2025-12-19T11:04:15.298282"
    },
    "result": {
      "type": "text",
      "text": "以下是为您精选的火锅分类餐厅推荐...(Qwen生成的推荐文案)"
    }
  }
}
```

---

## 各Skill参数说明

### 通用位置参数

所有支持位置的skill都可使用以下参数：

| 参数 | 类型 | 说明 | 示例 |
|------|------|------|------|
| `location` | string | 坐标（经度,纬度） | `"104.080989,30.657689"` |
| `address` | string | 详细地址 | `"成都市锦江区春熙路"` |
| `ip` | string | 用户IP地址 | `"120.24.xxx.xxx"` |
| `city` | string | 城市名称 | `"成都"` |

### smart_recommend - 智能推荐

```json
{
  "taste": "清淡",           // 可选: 清淡/辣/鲜
  "budget_max": 100,         // 可选: 最高预算(元)
  "budget_min": 0,           // 可选: 最低预算(元)
  "cuisine": "粤菜",         // 可选: 中餐/西餐/日料/韩餐/川菜/粤菜等
  "address": "广州市天河区珠江新城",
  "city": "广州"
}
```

### search_restaurant - 搜索餐厅

```json
{
  "keyword": "海底捞",    // 必需: 搜索关键词
  "city": "上海"          // 可选: 城市名
}
```

### browse_category - 分类浏览

```json
{
  "category": "火锅",           // 必需: 中餐/西餐/日料/韩餐/快餐/火锅/川菜/粤菜/湘菜等
  "address": "成都市锦江区春熙路",
  "city": "成都"
}
```

### recommend_by_taste - 按口味推荐

```json
{
  "taste": "辣",                // 必需: 清淡/辣/鲜
  "address": "重庆市渝中区解放碑",
  "city": "重庆"
}
```

### recommend_by_budget - 按预算推荐

```json
{
  "budget_max": 100,           // 必需: 最高预算
  "budget_min": 0,             // 可选: 最低预算
  "address": "北京市朝阳区三里屯",
  "city": "北京"
}
```

### get_restaurant_detail - 餐厅详情

```json
{
  "restaurant_name": "海底捞",  // 必需: 餐厅名称
  "restaurant_id": "B123...",   // 可选: POI ID (更精确)
  "city": "北京"
}
```

---

## 测试用例

当前 `quick_test.py` 包含以下测试：

| 测试 | Skill | 位置 | 预期结果 |
|------|-------|------|----------|
| 成都春熙路火锅 | browse_category | 地址 | 蜀大侠、和联潮汕牛肉火锅等 |
| 上海海底捞 | search_restaurant | 城市 | 5家海底捞门店 |
| 重庆解放碑辣味 | recommend_by_taste | 地址 | 水泊梁山鸡、醉湘亲老火锅 |
| 广州粤菜80元 | smart_recommend | 地址 | (条件严格可能无结果) |
| 北京三里屯日料 | browse_category | 地址 | 酬板前寿司、胜博殿等 |

---

## 常见问题

### Q: 服务启动失败？

检查：
1. Python版本 >= 3.10
2. 依赖是否安装完整：`pip install -r requirements.txt`
3. 端口8080是否被占用

### Q: API返回"暂无结果"？

检查：
1. 高德API Key是否正确配置
2. 搜索条件是否过于严格（如预算太低+口味+菜系同时限制）
3. location坐标格式是否正确（经度,纬度）
4. 地址是否准确（如"成都市武侯区天府广场"是错误的，天府广场在青羊区）

### Q: Qwen返回错误？

检查：
1. QWEN_API_KEY是否正确
2. 账户余额是否充足
3. 模型名称是否正确（qwen-turbo/qwen-plus/qwen-max）

### Q: 搜索结果不准确？

本项目搜索时同时使用 `keywords` 和 `types`（POI分类码）来提高准确性。如果仍有问题：
1. 检查 `poi.txt` 确认分类码是否正确
2. 尝试只用关键词搜索

### Q: IP定位不准确？

基础IP定位精度仅为城市级别。若需更精确定位：
1. 传入 `address` 参数（精确到街道）
2. 传入 `location` 参数（GPS坐标）
3. 或开通高德高级IP定位服务

---

## 技术说明

### 使用的高德API

- POI搜索 v3: `https://restapi.amap.com/v3/place/around` (周边搜索)
- POI搜索 v3: `https://restapi.amap.com/v3/place/text` (关键词搜索)
- 地理编码: `https://restapi.amap.com/v3/geocode/geo`
- IP定位: `https://restapi.amap.com/v3/ip`

### 搜索参数

- `keywords`: 搜索关键词（如"火锅"）
- `types`: POI分类码（如"050117"）
- 两者可同时使用，提高搜索准确性

---

## License

MIT
