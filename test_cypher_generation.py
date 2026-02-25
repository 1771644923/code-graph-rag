#!/usr/bin/env python3
"""
测试脚本：验证配置的 LLM 模型生成 Cypher 查询的能力

使用方法：
    python test_cypher_generation.py

这个脚本会使用你在 .env 中配置的 CYPHER_PROVIDER 和 CYPHER_MODEL
来测试模型是否能正确生成 Cypher 查询。
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


# 测试查询列表
TEST_QUERIES = [
    {
        "description": "列出所有类",
        "query": "List all classes in the codebase",
        "expected_contains": ["MATCH", "Class", "RETURN"],
    },
    {
        "description": "统计类的数量",
        "query": "How many classes are there?",
        "expected_contains": ["MATCH", "Class", "count", "RETURN"],
    },
    {
        "description": "查找特定文件",
        "query": "Find the main README.md file",
        "expected_contains": ["MATCH", "File", "RETURN"],
    },
    {
        "description": "查找 Python 文件",
        "query": "Find all Python files",
        "expected_contains": ["MATCH", "File", ".py", "RETURN"],
    },
    {
        "description": "查找特定类的方法",
        "query": "What methods does UserService have?",
        "expected_contains": ["MATCH", "Class", "Function", "RETURN"],
    },
]


def check_cypher_validity(cypher: str, expected_keywords: list[str]) -> tuple[bool, str]:
    """
    检查生成的 Cypher 查询是否有效
    
    返回: (是否有效, 错误信息)
    """
    # 检查基本结构
    cypher_upper = cypher.upper()
    
    # 必须包含 MATCH 关键字
    if "MATCH" not in cypher_upper:
        return False, "缺少 MATCH 关键字"
    
    # 必须包含 RETURN 关键字
    if "RETURN" not in cypher_upper:
        return False, "缺少 RETURN 关键字"
    
    # 检查期望的关键词
    missing_keywords = []
    for keyword in expected_keywords:
        if keyword.upper() not in cypher_upper:
            missing_keywords.append(keyword)
    
    if missing_keywords:
        return False, f"缺少期望的关键词: {', '.join(missing_keywords)}"
    
    # 检查是否有 LIMIT（对于列表查询）
    if "count" not in cypher_upper and "LIMIT" not in cypher_upper:
        logger.warning("⚠️  建议添加 LIMIT 子句以限制结果数量")
    
    return True, "OK"


async def test_cypher_generator():
    """测试 CypherGenerator 的生成能力"""
    
    logger.info("=" * 80)
    logger.info("开始测试 Cypher 查询生成能力")
    logger.info("=" * 80)
    logger.info("")
    
    try:
        # 初始化 CypherGenerator
        logger.info("正在初始化 CypherGenerator...")
        generator = CypherGenerator()
        logger.success("✓ CypherGenerator 初始化成功")
        logger.info("")
    except Exception as e:
        logger.error(f"✗ CypherGenerator 初始化失败: {e}")
        logger.error("请检查 .env 文件中的 CYPHER_PROVIDER 和 CYPHER_MODEL 配置")
        return
    
    # 统计结果
    total_tests = len(TEST_QUERIES)
    passed_tests = 0
    failed_tests = 0
    
    # 运行测试
    for i, test_case in enumerate(TEST_QUERIES, 1):
        logger.info(f"测试 {i}/{total_tests}: {test_case['description']}")
        logger.info(f"  自然语言查询: {test_case['query']}")
        
        try:
            # 生成 Cypher 查询
            cypher = await generator.generate(test_case['query'])
            
            # 检查查询有效性
            is_valid, message = check_cypher_validity(cypher, test_case['expected_contains'])
            
            if is_valid:
                logger.success(f"  ✓ 成功生成有效的 Cypher 查询")
                logger.info(f"  生成的查询:")
                logger.info(f"  {cypher}")
                passed_tests += 1
            else:
                logger.error(f"  ✗ 查询无效: {message}")
                logger.info(f"  生成的查询:")
                logger.info(f"  {cypher}")
                failed_tests += 1
                
        except ex.LLMGenerationError as e:
            logger.error(f"  ✗ LLM 生成失败: {e}")
            failed_tests += 1
        except Exception as e:
            logger.error(f"  ✗ 未知错误: {e}")
            failed_tests += 1
        
        logger.info("")
    
    # 输出总结
    logger.info("=" * 80)
    logger.info("测试总结")
    logger.info("=" * 80)
    logger.info(f"总测试数: {total_tests}")
    logger.success(f"通过: {passed_tests}")
    logger.error(f"失败: {failed_tests}")
    logger.info("")
    
    if failed_tests == 0:
        logger.success("🎉 所有测试通过！你的模型配置可以正常生成 Cypher 查询。")
    elif passed_tests == 0:
        logger.error("❌ 所有测试都失败了。建议：")
        logger.error("  1. 检查 .env 配置是否正确")
        logger.error("  2. 尝试使用更强的模型（如 GPT-4o-mini、codellama 等）")
        logger.error("  3. 确保模型可以正常访问（API 密钥、网络连接等）")
    else:
        logger.warning(f"⚠️  部分测试通过 ({passed_tests}/{total_tests})。")
        logger.warning("模型可能需要调整配置或更换更强的模型。")
    
    logger.info("=" * 80)


def main():
    """主函数"""
    try:
        asyncio.run(test_cypher_generator())
    except KeyboardInterrupt:
        logger.warning("\n测试被用户中断")
    except Exception as e:
        logger.error(f"\n测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()