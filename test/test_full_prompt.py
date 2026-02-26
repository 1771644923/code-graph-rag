#!/usr/bin/env python3
"""
使用完整的 LOCAL_CYPHER_SYSTEM_PROMPT 测试 openai_compatible 模型
"""

import asyncio
from pathlib import Path

from loguru import logger
from dotenv import load_dotenv

# 加载环境变量
env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)

from codebase_rag.config import ModelConfig, settings
from codebase_rag.prompts import LOCAL_CYPHER_SYSTEM_PROMPT


async def test_with_full_prompt():
    """使用完整的系统提示测试模型"""
    
    logger.info("=" * 80)
    logger.info("使用完整 LOCAL_CYPHER_SYSTEM_PROMPT 测试")
    logger.info("=" * 80)
    logger.info("")
    
    # 显示配置
    config = settings.active_cypher_config
    logger.info("当前模型配置:")
    logger.info(f"  Provider: {config.provider}")
    logger.info(f"  Model: {config.model_id}")
    logger.info(f"  Endpoint: {config.endpoint}")
    logger.info("")
    
    # 显示系统提示长度
    logger.info(f"LOCAL_CYPHER_SYSTEM_PROMPT 长度: {len(LOCAL_CYPHER_SYSTEM_PROMPT)} 字符")
    logger.info("")
    
    # 测试查询
    test_query = "List all classes in the codebase"
    
    logger.info(f"测试查询: {test_query}")
    logger.info("")
    
    try:
        # 导入必要的模块
        from codebase_rag.services.llm import _create_provider_model
        from pydantic_ai import Agent
        
        # 创建模型
        model = _create_provider_model(config)
        
        # 创建 Agent，使用完整的系统提示
        agent = Agent(
            model=model,
            system_prompt=LOCAL_CYPHER_SYSTEM_PROMPT,
            output_type=str,
            retries=3,
        )
        
        logger.info("正在调用模型...")
        result = await agent.run(test_query)
        
        logger.info("-" * 80)
        logger.info("模型原始输出:")
        logger.info("-" * 80)
        logger.info(result.output)
        logger.info("-" * 80)
        logger.info("")
        
        # 分析输出
        output_upper = result.output.upper()
        
        if "MATCH" in output_upper and "RETURN" in output_upper:
            logger.success("✓ 输出包含 MATCH 和 RETURN 关键字")
            logger.success("✓ 模型成功生成了 Cypher 查询！")
            logger.info("")
            logger.info("结论：当前的 LOCAL_CYPHER_SYSTEM_PROMPT 可以正常工作")
        else:
            logger.error("✗ 输出不包含必需的 Cypher 关键字")
            logger.error("")
            logger.error("模型返回的是解释性文本而非 Cypher 查询")
            logger.error("")
            logger.error("建议：")
            logger.error("  1. 进一步简化系统提示")
            logger.error("  2. 或者更换为更强的模型（GPT-4o-mini、Gemini 等）")
        
    except Exception as e:
        logger.error(f"✗ 错误: {e}")
        import traceback
        traceback.print_exc()
    
    logger.info("")
    logger.info("=" * 80)


def main():
    """主函数"""
    try:
        asyncio.run(test_with_full_prompt())
    except KeyboardInterrupt:
        logger.warning("\n测试被用户中断")
    except Exception as e:
        logger.error(f"\n测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()