"""测试京东云 API - 带额外的请求头"""
import asyncio
from openai import AsyncOpenAI


async def test_jdcloud_api():
    """测试京东云 API"""
    
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
        
        # 尝试不同的模型名称
        models_to_test = [
            "kimi2.5-pro",
            "kimi-2.5-pro",
            "kimi",
            "Chatrhino-750B",
        ]
        
        for model_name in models_to_test:
            print(f"\n测试模型: {model_name}")
            try:
                response = await client.chat.completions.create(
                    model=model_name,
                    messages=[
                        {"role": "user", "content": "你好"}
                    ],
                    max_tokens=50
                )
                print(f"✓ 成功! 响应: {response.choices[0].message.content}")
                print(f"\n✅ 模型名称 {model_name} 可用！")
                return model_name
            except Exception as e:
                print(f"✗ 失败: {e}")
                continue
        
        print("\n❌ 所有模型名称都测试失败")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_jdcloud_api())