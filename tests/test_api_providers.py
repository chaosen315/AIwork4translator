import pytest
from modules.api_tool import KimiProvider, DeepseekProvider, SillionProvider, GeminiProvider, DoubaoProvider
import os
from dotenv import load_dotenv

load_dotenv("data/.env")
# 测试用例：仿真的一句话翻译场景
TEST_TERMS_DICT = {"night city": "夜之城"}
TEST_ORIGINAL_TEXT = "Night City was like a deranged experiment in social Darwinism, designed by a bored researcher who kept one thumb permanently on the fast-forward button."
TEST_SYSTEM_PROMPT = "你是一个专业的翻译助手，请将英文文本翻译成中文，注意保留术语表中的专有名词翻译。"

# 构建完整的测试prompt
TEST_PROMPT = f"提供术语表：{TEST_TERMS_DICT}。原文：{TEST_ORIGINAL_TEXT}"

@pytest.mark.parametrize("provider_class, provider_name", [
    (KimiProvider, "kimi"),
    (DeepseekProvider, "deepseek"),
    (SillionProvider, "sillion"),
    (GeminiProvider, "gemini"),
    (DoubaoProvider, "doubao"),
])
def test_api_provider_availability(provider_class, provider_name):
    """
    测试各个API provider的可用性，通过真实调用API进行翻译测试
    """
    try:

        # 初始化provider
        provider = provider_class()
        
        # 调用API进行翻译
        result, total_tokens = provider.generate_completion(TEST_PROMPT, TEST_SYSTEM_PROMPT)
        
        # 验证结果
        assert result is not None, f"{provider_name} API调用返回结果为空"
        assert isinstance(result, str), f"{provider_name} API调用返回结果不是字符串类型"
        assert len(result.strip()) > 0, f"{provider_name} API调用返回结果为空字符串"
        assert isinstance(total_tokens, int), f"{provider_name} API调用返回的token数不是整数类型"
        assert total_tokens > 0, f"{provider_name} API调用返回的token数必须大于0"
        
        # 验证翻译结果中包含正确的术语翻译
        assert "夜之城" in result, f"{provider_name} API调用未正确使用术语表翻译'night city'为'夜之城'"
        
        print(f"\n{provider_name} API测试通过！")
        print(f"翻译结果：{result}")
        print(f"使用token数：{total_tokens}")
        
    except Exception as e:
        pytest.fail(f"{provider_name} API测试失败：{str(e)}")
