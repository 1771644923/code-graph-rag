#!/usr/bin/env python3
"""
调试脚本：验证 Cypher 查询生成并显示详细调试信息

使用方法：
    python test_cypher_with_debug.py

这个脚本会显示：
1. 使用的模型配置
2. 使用的系统提示
3. 测试查询的生成过程
"""

import asyncio
from pathlib import Path

from loguru import logger
from dotenv import load_dotenv

# 加载环境变量
env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)

from codebase_rag.services.llm import CypherGenerator
from codebase_rag import exceptions as ex
from codebase_rag import config


async def test_with_debug():
    """测试并显示调试信息"""
    
    logger.info("=" * 80)
    logger.info("Cypher 生成调试测试")
    logger.info("=" * 80)
    logger.info("")
    
    # 显示当前配置
    logger.info("当前配置:")
    logger.info(f"  CYPHER_PROVIDER: {config.settings.active_cypher_config.provider}")
    logger.info(f"  CYPHER_MODEL: {config.settings.active_cypher_config.model_id}")
    logger.info(f"  CYPHER_ENDPOINT: {config.settings.active_cypher_config.endpoint}")
    logger.info("")
    
    try:
        # 初始化 CypherGenerator
        logger.info("正在初始化 CypherGenerator...")
        generator = CypherGenerator()
        logger.success("✓ CypherGenerator 初始化成功")
        logger.info("")
        
        # 显示系统提示
        logger.info("系统提示 (前 500 字符):")
        logger.info("-" * 80)
        system_prompt = generator.agent._system_prompt or "N/A"
        if system_prompt != "N/A":
            logger.info(system_prompt[:500] + "..." if len(system_prompt) > 500 else system_prompt)
        else:
            logger.info("无法获取系统提示")
        logger.info("-" * 80)
        logger.info("")
        
    except Exception as e:
        logger.error(f"✗ CypherGenerator 初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # 测试查询
    test_query = "List all classes in the codebase"
    
    logger.info(f"测试查询: {test_query}")
    logger.info("")
    
    try:
        # 生成 Cypher 查询
        result = await generator.agent.run(test_query)
        
        logger.info("LLM 原始输出:")
        logger.info("-" * 80)
        logger.info(result.output)
        logger.info("-" * 80)
        logger.info("")
        
        # 验证输出
        if "MATCH" in result.output.upper():
            logger.success("✓ 输出包含 MATCH 关键字")
        else:
            logger.error("✗ 输出不包含 MATCH 关键字 - 这就是问题所在!")
            logger.error("")
            logger.error("可能的原因:")
            logger.error("  1. 模型不理解系统提示")
            logger.error("  2. 模型被训练为总是返回解释而非代码")
            logger.error("  3. 模型能力不足，无法生成 Cypher 查询")
            logger.error("")
            logger.error("建议:")
            logger.error("  1. 尝试使用 GPT-4o-mini 或其他更强的模型")
            logger.error("  2. 如果使用本地模型，确保是代码生成模型（如 codellama）")
            logger.error("  3. 检查 API 端点是否返回正确的模型")
        
        logger.info("")
        
    except ex.LLMGenerationError as e:
        logger.error(f"✗ LLM 生成失败: {e}")
    except Exception as e:
        logger.error(f"✗ 未知错误: {e}")
        import traceback
        traceback.print_exc()
    
    logger.info("")
    logger.info("=" * 80)


def main():
    """主函数"""
    try:
        asyncio.run(test_with_debug())
    except KeyboardInterrupt:
        logger.warning("\n测试被用户中断")
    except Exception as e:
        logger.error(f"\n测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()