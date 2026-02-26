"""测试京东云 API - 带自定义请求头"""
import asyncio
import json
from openai import AsyncOpenAI


async def test_jdcloud_with_headers():
    """测试京东云 API，带自定义请求头"""
    
    # 配置
    api_key = "pk-34008311-7035-4727-800c-059e397dc2f7"
    base_url = "https://modelservice.jdcloud.com/v1"
    
    print(f"API Key: {api_key[:20]}...")
    print(f"Base URL: {base_url}")
    
    try:
        # 创建客户端
        client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url
        )
        
        # 尝试直接使用原始的 HTTP 请求来调试
        import httpx
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "kimi2.5-pro",
            "messages": [{"role": "user", "content": "你好"}],
            "max_tokens": 50
        }
        
        print("\n尝试 1: 直接 HTTP 请求到 chat/completions 端点")
        try:
            async with httpx.AsyncClient() as http_client:
                response = await http_client.post(
                    f"{base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=30
                )
                print(f"状态码: {response.status_code}")
                print(f"响应: {response.text[:500]}")
                
                if response.status_code == 200:
                    print("✅ 成功！")
                    return
        except Exception as e:
            print(f"✗ 失败: {e}")
        
        # 尝试不同的端点
        endpoints_to_test = [
            "/chat/completions",
            "/v1/chat/completions",
        ]
        
        for endpoint in endpoints_to_test:
            print(f"\n尝试端点: {endpoint}")
            try:
                async with httpx.AsyncClient() as http_client:
                    response = await http_client.post(
                        f"{base_url}{endpoint}",
                        headers=headers,
                        json=payload,
                        timeout=30
                    )
                    print(f"状态码: {response.status_code}")
                    if response.status_code != 404:
                        print(f"响应: {response.text[:500]}")
                        if response.status_code == 200:
                            print("✅ 成功！")
                            return
            except Exception as e:
                print(f"✗ 失败: {e}")
        
        print("\n❌ 所有尝试都失败")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_jdcloud_with_headers())