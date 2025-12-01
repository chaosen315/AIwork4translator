import os
import traceback
from modules.api_tool import KimiProvider, DeepseekProvider, SillionProvider, GeminiProvider, DoubaoProvider
from dotenv import load_dotenv

load_dotenv("data/.env")
# 打印环境变量状态
def print_env_status():
    print("=== 环境变量状态 ===")
    env_vars = [
        "KIMI_API_KEY", "KIMI_BASE_URL",
        "DEEPSEEK_API_KEY", "DEEPSEEK_BASE_URL",
        "SILLION_API_KEY", "SILLION_BASE_URL",
        "GEMINI_API_KEY",
        "DOUBAO_API_KEY", "DOUBAO_BASE_URL"
    ]
    for var in env_vars:
        value = os.getenv(var)
        if value:
            print(f"✓ {var}: 已设置")
        else:
            print(f"✗ {var}: 未设置")

# 测试用例：仿真的一句话翻译场景
TEST_TERMS_DICT = {"night city": "夜之城"}
TEST_ORIGINAL_TEXT = "Night City was like a deranged experiment in social Darwinism, designed by a bored researcher who kept one thumb permanently on the fast-forward button."
TEST_SYSTEM_PROMPT = "你是一个专业的翻译助手，请将英文文本翻译成中文，注意保留术语表中的专有名词翻译。"

# 构建完整的测试prompt
TEST_PROMPT = f"提供术语表：{TEST_TERMS_DICT}。原文：{TEST_ORIGINAL_TEXT}"

# 要测试的provider列表
providers_to_test = [
    (KimiProvider, "kimi"),
    (DeepseekProvider, "deepseek"),
    (SillionProvider, "sillion"),
    (GeminiProvider, "gemini"),
    (DoubaoProvider, "doubao"),
]

# 执行测试
print("开始API provider测试...")
print_env_status()

success_count = 0
fail_count = 0

for provider_class, provider_name in providers_to_test:
    print(f"\n=== 测试 {provider_name} API ===")
    try:
        # 初始化provider
        print(f"正在初始化 {provider_name}...")
        provider = provider_class()
        print(f"✓ {provider_name} 初始化成功")
        
        # 调用API进行翻译
        print(f"正在调用 {provider_name} API...")
        result, total_tokens = provider.generate_completion(TEST_PROMPT, TEST_SYSTEM_PROMPT)
        
        # 验证结果
        if result is not None and isinstance(result, str) and len(result.strip()) > 0:
            print(f"✓ {provider_name} API调用成功")
            print(f"翻译结果：{result}")
            print(f"使用token数：{total_tokens}")
            
            # 验证术语翻译
            if "夜之城" in result:
                print(f"✓ {provider_name} 正确使用术语表翻译'night city'为'夜之城'")
            else:
                print(f"✗ {provider_name} 未正确使用术语表翻译'night city'为'夜之城'")
            
            success_count += 1
        else:
            print(f"✗ {provider_name} API调用返回结果无效")
            print(f"返回结果：{result}")
            fail_count += 1
            
    except Exception as e:
        print(f"✗ {provider_name} API测试失败：{str(e)}")
        print(f"详细错误信息：")
        traceback.print_exc()
        fail_count += 1

print(f"\n=== 测试完成 ===")
print(f"测试结果：成功 {success_count} 个，失败 {fail_count} 个")
print(f"总测试数：{len(providers_to_test)}")
