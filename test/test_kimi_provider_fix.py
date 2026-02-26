"""测试 Kimi Provider 端点修复"""
import os
from dotenv import load_dotenv

load_dotenv()

from codebase_rag.providers.base import KimiProvider, get_provider_from_config
from codebase_rag.config import settings


def test_kimi_provider_with_none_endpoint():
    """测试当 endpoint 为 None 时使用默认值"""
    print("测试 1: KimiProvider(endpoint=None)")
    provider = KimiProvider(api_key='test-key', endpoint=None)
    assert provider.endpoint == 'https://modelservice.jdcloud.com/v1', \
        f"Expected default endpoint, got {provider.endpoint}"
    print(f"✓ 正确使用默认端点: {provider.endpoint}")


def test_kimi_provider_with_custom_endpoint():
    """测试使用自定义端点"""
    print("\n测试 2: KimiProvider(endpoint='custom')")
    provider = KimiProvider(api_key='test-key', endpoint='https://custom.api.com/v1')
    assert provider.endpoint == 'https://custom.api.com/v1', \
        f"Expected custom endpoint, got {provider.endpoint}"
    print(f"✓ 正确使用自定义端点: {provider.endpoint}")


def test_config_loading():
    """测试从配置加载"""
    print("\n测试 3: 从配置加载")
    config = settings.active_orchestrator_config
    print(f"  - Provider: {config.provider}")
    print(f"  - Model: {config.model_id}")
    print(f"  - Endpoint (原始): {config.endpoint}")
    
    # 通过 get_provider_from_config 创建 provider
    provider = get_provider_from_config(config)
    print(f"  - Provider endpoint (处理后): {provider.endpoint}")
    
    # 验证 endpoint 不为 None
    assert provider.endpoint is not None, "Provider endpoint should not be None"
    assert provider.endpoint == 'https://modelservice.jdcloud.com/v1', \
        f"Expected JD Cloud endpoint, got {provider.endpoint}"
    print(f"✓ 正确从配置创建 provider，使用默认端点")


def test_model_creation():
    """测试模型创建"""
    print("\n测试 4: 创建模型")
    provider = KimiProvider(api_key='test-key', endpoint=None)
    model = provider.create_model('Kimi-K2.5')
    
    # 检查 model 的 provider 配置
    print(f"  - Model created: {model}")
    print(f"  - Model provider base_url: {model._provider.base_url}")
    # pydantic-ai 会自动在 base_url 后面添加斜杠
    assert 'modelservice.jdcloud.com' in model._provider.base_url, \
        f"Expected JD Cloud base_url, got {model._provider.base_url}"
    assert 'api.openai.com' not in model._provider.base_url, \
        f"Should not use OpenAI endpoint, got {model._provider.base_url}"
    print(f"✓ 模型正确创建，使用正确的 base_url")


if __name__ == "__main__":
    try:
        test_kimi_provider_with_none_endpoint()
        test_kimi_provider_with_custom_endpoint()
        test_config_loading()
        test_model_creation()
        print("\n" + "="*50)
        print("✅ 所有测试通过！修复成功！")
        print("="*50)
    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()