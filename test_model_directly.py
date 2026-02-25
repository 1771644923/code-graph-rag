#!/usr/bin/env python3
"""
直接测试 LLM 模型生成 Cypher 查询的能力
绕过验证逻辑，查看模型的原始输出
"""

import asyncio
from pathlib import Path

from loguru import logger
from dotenv import load_dotenv

# 加载环境变量
env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)

from codebase_rag.config import ModelConfig, settings


# 简化的 Cypher 查询生成提示
CYHER_GENERATION_PROMPT = """You are a Neo4j Cypher query generator. You ONLY respond with a valid Cypher query. Do not add explanations or markdown.

**CRITICAL RULES:**
1. Your query must start with MATCH
2. Your query must end with RETURN
3. Do not include any explanations or text outside the Cypher query
4. Do not use markdown code blocks (```)
5. Return ONLY the Cypher query itself

**Query to generate:** {query}

**Cypher Query:**"""


async def test_model_directly():
    """直接测试模型生成 Cypher 的能力"""
    
    logger.info("=" * 80)
    logger.info("直接测试 LLM 模型生成 Cypher 查询")
    logger.info("=" * 80)
    logger.info("")
    
    # 显示配置
    config = settings.active_cypher_config
    logger.info("当前模型配置:")
    logger.info(f"  Provider: {config.provider}")
    logger.info(f"  Model: {config.model_id}")
    logger.info(f"  Endpoint: {config.endpoint}")
    logger.info("")
    
    # 测试查询列表
    test_queries = [
        "List all classes in the codebase",
        "How many classes are there?",
        "Find all Python files",
    ]
    
    for i, query in enumerate(test_queries, 1):
        logger.info(f"测试 {i}/{len(test_queries)}: {query}")
        logger.info("-" * 80)
        
        try:
            # 构造提示
            prompt = CYHER_GENERATION_PROMPT.format(query=query)
            
            logger.info(f"发送给模型的提示:")
            logger.info(prompt)
            logger.info("")
            
            # 使用 pydantic-ai 直接调用模型
            from codebase_rag.services.llm import _create_provider_model
            model = _create_provider_model(config)
            
            # 调用模型
            from pydantic_ai import Agent
            agent = Agent(model, system_prompt="You are a Cypher query generator.")
            
            result = await agent.run(prompt)
            
            logger.info(f"模型原始输出:")
            logger.info(result.output)
            logger.info("")
            
            # 分析输出
            output_upper = result.output.upper()
            if "MATCH" in output_upper and "RETURN" in output_upper:
                logger.success("✓ 输出看起来像 Cypher 查询")
                
                # 尝试清理输出
                cleaned = result.output.strip()
                if cleaned.startswith("```"):
                    cleaned = cleaned[3:]
                if cleaned.endswith("```"):
                    cleaned = cleaned[:-3]
                cleaned = cleaned.strip()
                
                if "cypher" in cleaned.lower()[:10]:
                    cleaned = cleaned[6:].strip()
                
                logger.info(f"清理后的查询:")
                logger.info(cleaned)
            else:
                logger.error("✗ 输出不是有效的 Cypher 查询")
                logger.error("")
                logger.error("模型返回的是解释性文本，而不是 Cypher 查询")
                logger.error("这说明该模型不适合用于 Cypher 查询生成任务")
        
        except Exception as e:
            logger.error(f"✗ 错误: {e}")
            import traceback
            traceback.print_exc()
        
        logger.info("")
        logger.info("=" * 80)
        logger.info("")
    
    logger.info("")
    logger.info("总结:")
    logger.info("如果所有测试都失败（模型返回解释而非 Cypher 查询），")
    logger.info("说明当前配置的模型不适合 Cypher 查询生成任务。")
    logger.info("")
    logger.info("建议:")
    logger.info("  1. 切换到专门用于代码生成的模型（如 codellama、GPT-4o-mini）")
    logger.info("  2. 或者联系模型提供商，确认该模型是否支持代码生成")


def main():
    """主函数"""
    try:
        asyncio.run(test_model_directly())
    except KeyboardInterrupt:
        logger.warning("\n测试被用户中断")
    except Exception as e:
        logger.error(f"\n测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()