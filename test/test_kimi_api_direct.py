"""直接测试 Kimi API"""
import asyncio
from openai import AsyncOpenAI


async def test_kimi_api():
    """直接测试 Kimi API"""
    
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
        
        # 测试调用 - 先使用 moonshot-v1 模型
        print("\n测试 1: 使用 moonshot-v1-8k 模型...")
        response = await client.chat.completions.create(
            model="moonshot-v1-8k",
            messages=[
                {"role": "user", "content": "你好"}
            ],
            max_tokens=50
        )
        print(f"✓ 成功! 响应: {response.choices[0].message.content}")
        
        # 测试调用 - 尝试 kimi-2.5-pro
        print("\n测试 2: 使用 kimi-2.5-pro 模型...")
        response = await client.chat.completions.create(
            model="kimi-2.5-pro",
            messages=[
                {"role": "user", "content": "你好"}
            ],
            max_tokens=50
        )
        print(f"✓ 成功! 响应: {response.choices[0].message.content}")
        
        print("\n✅ API 测试成功！")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_kimi_api())