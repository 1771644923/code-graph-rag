"""测试 Kimi provider 是否可用"""
import asyncio
import os
from codebase_rag.providers.base import get_provider
from pydantic_ai import Agent
from loguru import logger


async def test_kimi_provider():
    """测试 Kimi provider"""
    
    # 测试配置
    api_key = "pk-34008311-7035-4727-800c-059e397dc2f7"
    # Kimi 2.5 模型名称格式
    model_ids_to_test = [
        "kimi-2.5-pro",      # Kimi 2.5 Pro
        "kimi-2.5-exp",      # Kimi 2.5 实验版
        "kimi-2.5-mini",     # Kimi 2.5 Mini
    ]
    model_id = model_ids_to_test[0]  # 先测试 pro 版本
    
    logger.info("开始测试 Kimi provider...")
    logger.info(f"API Key: {api_key[:20]}...")
    logger.info(f"Models to test: {model_ids_to_test}")
    logger.info(f"Testing with: {model_id}")
    
    try:
        # 1. 创建 provider
        logger.info("\n1. 创建 KimiProvider...")
        provider = get_provider(
            provider_name="kimi",
            api_key=api_key
        )
        logger.info(f"✓ Provider 创建成功: {provider.provider_name}")
        
        # 2. 创建模型
        logger.info("\n2. 创建模型实例...")
        model = provider.create_model(model_id)
        logger.info(f"✓ 模型创建成功: {model}")
        
        # 3. 创建 Agent 并测试调用
        logger.info("\n3. 创建 Agent 并测试简单对话...")
        agent = Agent(model, system_prompt="你是一个有帮助的AI助手。")
        
        # 测试简单对话
        response = await agent.run("你好，请用一句话介绍一下你自己。")
        logger.info(f"✓ 模型响应: {response.data}")
        
        # 4. 测试代码相关任务
        logger.info("\n4. 测试代码相关任务...")
        code_task = "请用 Python 写一个简单的函数，计算两个数的和。"
        response = await agent.run(code_task)
        logger.info(f"✓ 代码生成响应:\n{response.data}")
        
        logger.info("\n✅ 所有测试通过！Kimi provider 工作正常。")
        return True
        
    except Exception as e:
        logger.error(f"\n❌ 测试失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


if __name__ == "__main__":
    result = asyncio.run(test_kimi_provider())
    if result:
        print("\n✨ Kimi 2.5 适配成功，可以正常使用！")
    else:
        print("\n⚠️ 测试失败，请检查配置")