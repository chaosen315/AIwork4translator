import asyncio
import sys
import os
import pytest
from unittest.mock import MagicMock

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from modules.translation_core import TranslationCore, TranslationResult
from modules.api_tool import LLMService

@pytest.mark.asyncio
async def test_fallback():
    # Mock LLMService
    mock_llm = MagicMock(spec=LLMService)
    
    # Complex content with MD syntax, Chinese quotes, and English quotes (escaped)
    # Scenario:
    # 1. **Bold** and *Italic*
    # 2. Chinese quotes: “中文”
    # 3. Escaped English quotes: \"English\"
    # 4. Escaped newlines: \n
    # 5. Invalid JSON structure at the end
    
    # We use raw string for the content inside the JSON string value
    # In a JSON file, it would look like: "translation": "..."
    complex_inner_content = r'这里有 **粗体** 和 *斜体*。\n还有“中文引号”和 \"英文引号\"。\n以及代码 `code`。'
    
    # Construct the full "origin_text"
    origin_text = f'{{"translation": "{complex_inner_content}", "notes": "Complex notes.", "invalid": '
    
    error_response = {
        "origin_text": origin_text,
        "error": "Invalid JSON format"
    }
    
    # Mock methods
    mock_llm.call_ai_model_api.return_value = (error_response, 100)
    mock_llm.create_prompt.return_value = "prompt"
    mock_llm.repair_json.return_value = (error_response, 50)
    mock_llm.rewrite_with_glossary.return_value = ({"translation": "rewritten", "new_terms": []}, 10)

    core = TranslationCore(mock_llm)
    
    segment = {"content": "Source text"}
    terms_dict = {}
    aggregated_new_terms = {}
    
    print("Starting translation step test with COMPLEX content...")
    print(f"Origin Text Mock: {origin_text}")
    
    result = await core.execute_translation_step(
        segment, 
        terms_dict, 
        aggregated_new_terms,
        max_api_retries=1
    )
    
    print("-" * 50)
    print(f"Result Success: {result.success}")
    print(f"Result Content (Raw): {result.content!r}")
    print(f"Result Notes: {result.notes}")
    print("-" * 50)
    
    # Expected content verification:
    # 1. \n should become actual newline
    # 2. \" should become "
    expected_content = complex_inner_content.replace(r'\"', '"').replace(r'\n', '\n')
    
    print(f"Expected Content (Raw): {expected_content!r}")
    
    if result.success and result.content == expected_content:
        print("TEST PASSED: Fallback logic worked for complex content.")
    else:
        print("TEST FAILED: Fallback logic did not produce expected result.")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(test_fallback())
