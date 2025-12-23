"""Quick Test - Test all 3 skills (v2.0)"""
import httpx
import asyncio
import json

async def test():
    url = "http://localhost:8080/a2a"
    results = []

    async with httpx.AsyncClient(timeout=60.0) as client:

        # Test 1: recommend - 综合条件推荐（口味+预算+菜系）
        print("[1/5] Testing recommend - 综合条件...")
        payload1 = {
            "jsonrpc": "2.0",
            "id": "test-001",
            "method": "tasks/send",
            "params": {
                "id": "task-001",
                "skill_id": "recommend",
                "params": {
                    "taste": "辣",
                    "budget_max": 80,
                    "cuisine": "川菜",
                    "address": "成都市锦江区春熙路",
                    "city": "成都"
                }
            }
        }
        resp1 = await client.post(url, json=payload1)
        results.append({
            "test": "recommend - 成都春熙路辣味川菜80元内",
            "skill_id": "recommend",
            "response": resp1.json()
        })
        print("[OK] done")

        # Test 2: recommend - 仅口味
        print("[2/5] Testing recommend - 仅口味...")
        payload2 = {
            "jsonrpc": "2.0",
            "id": "test-002",
            "method": "tasks/send",
            "params": {
                "id": "task-002",
                "skill_id": "recommend",
                "params": {
                    "taste": "清淡",
                    "address": "广州市天河区珠江新城",
                    "city": "广州"
                }
            }
        }
        resp2 = await client.post(url, json=payload2)
        results.append({
            "test": "recommend - 广州珠江新城清淡口味",
            "skill_id": "recommend",
            "response": resp2.json()
        })
        print("[OK] done")

        # Test 3: recommend - 仅菜系/分类
        print("[3/5] Testing recommend - 仅菜系...")
        payload3 = {
            "jsonrpc": "2.0",
            "id": "test-003",
            "method": "tasks/send",
            "params": {
                "id": "task-003",
                "skill_id": "recommend",
                "params": {
                    "cuisine": "日料",
                    "address": "深圳市南山区科技园",
                    "city": "深圳"
                }
            }
        }
        resp3 = await client.post(url, json=payload3)
        results.append({
            "test": "recommend - 深圳科技园日料",
            "skill_id": "recommend",
            "response": resp3.json()
        })
        print("[OK] done")

        # Test 4: search - 搜索餐厅
        print("[4/5] Testing search...")
        payload4 = {
            "jsonrpc": "2.0",
            "id": "test-004",
            "method": "tasks/send",
            "params": {
                "id": "task-004",
                "skill_id": "search",
                "params": {
                    "keyword": "海底捞",
                    "city": "上海"
                }
            }
        }
        resp4 = await client.post(url, json=payload4)
        results.append({
            "test": "search - 上海海底捞",
            "skill_id": "search",
            "response": resp4.json()
        })
        print("[OK] done")

        # Test 5: detail - 餐厅详情
        print("[5/5] Testing detail...")
        payload5 = {
            "jsonrpc": "2.0",
            "id": "test-005",
            "method": "tasks/send",
            "params": {
                "id": "task-005",
                "skill_id": "detail",
                "params": {
                    "restaurant_name": "肯德基",
                    "city": "北京"
                }
            }
        }
        resp5 = await client.post(url, json=payload5)
        results.append({
            "test": "detail - 北京肯德基详情",
            "skill_id": "detail",
            "response": resp5.json()
        })
        print("[OK] done")

    # Save results
    with open("test_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print("\n" + "="*50)
    print("All 5 tests completed! Results saved to test_results.json")
    print("="*50)

    # Print summary
    print("\nSummary:")
    for r in results:
        status = r["response"].get("result", {}).get("status", {}).get("state", "unknown")
        text = r["response"].get("result", {}).get("result", {}).get("text", "")[:50]
        print(f"  [{status}] {r['test']}")
        if "抱歉" in text or "未找到" in text:
            print(f"           ⚠️ {text}...")

if __name__ == "__main__":
    asyncio.run(test())
