import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from modules.translation_core import TranslationCore, RepairPolicy
from modules.api_tool import LLMService

@pytest.mark.asyncio
async def test_conservative_fallback_preserves_markdown_body():
    mock_llm = MagicMock(spec=LLMService)

    recovered_body = "# 标题\n\n- 列表项\n\n```python\nprint(1)\n```"
    escaped_body = recovered_body.replace("\\", "\\\\").replace("\n", r"\n")
    origin_text = (
        "{'translation': '" + escaped_body + "', "
        "'notes': '- 术语：保守恢复', "
        "'new_terms': ["
    )
    error_response = {
        "origin_text": origin_text,
        "error": "Invalid JSON format"
    }

    mock_llm.call_ai_model_api_async = AsyncMock(return_value=(error_response, 100))
    mock_llm.create_prompt.return_value = "prompt"
    mock_llm.repair_json_async = AsyncMock(return_value=(error_response, 50))
    mock_llm.rewrite_with_glossary_async = AsyncMock(return_value=({"translation": "rewritten", "new_terms": []}, 10))

    core = TranslationCore(mock_llm)

    with patch("modules.translation_core.asyncio.sleep", new=AsyncMock()):
        result = await core.execute_translation_step(
            {"content": "Source text"},
            {},
            {},
            repair_policy=RepairPolicy.NONE,
            max_api_retries=1,
        )

    assert result.success
    assert result.content == recovered_body
    assert "保守解析恢复" in result.notes
    assert "- 术语：保守恢复" in result.notes
    assert result.new_terms_delta == []

@pytest.mark.asyncio
async def test_conservative_fallback_handles_unquoted_translation_key():
    mock_llm = MagicMock(spec=LLMService)
    origin_text = '{translation: "正文\\n\\n## 小节", notes: "注释未完全闭合", new_terms: [}'
    error_response = {"origin_text": origin_text, "error": "Invalid JSON format"}

    mock_llm.call_ai_model_api_async = AsyncMock(return_value=(error_response, 30))
    mock_llm.create_prompt.return_value = "prompt"
    mock_llm.repair_json_async = AsyncMock(return_value=(error_response, 10))

    core = TranslationCore(mock_llm)

    with patch("modules.translation_core.asyncio.sleep", new=AsyncMock()):
        result = await core.execute_translation_step(
            {"content": "Source text"},
            {},
            {},
            repair_policy=RepairPolicy.NONE,
            max_api_retries=1,
        )

    assert result.success
    assert result.content == "正文\n\n## 小节"
    assert "保守解析恢复" in result.notes

@pytest.mark.asyncio
async def test_targeted_fallback_uses_conservative_prompt_for_high_risk_content():
    mock_llm = MagicMock(spec=LLMService)
    mock_llm.provider = "gpt"
    mock_llm.create_prompt.return_value = "base prompt"
    mock_llm.call_ai_model_api_async = AsyncMock(return_value=(
        {
            "translation": "| 名称 | 值 |\n| --- | --- |\n| alpha | one |",
            "notes": "原始注释",
            "new_terms": [{"term": "alpha", "translation": "阿尔法", "reason": "sample"}],
        },
        42,
    ))
    mock_llm.repair_json_async = AsyncMock()
    mock_llm.rewrite_with_glossary_async = AsyncMock()

    core = TranslationCore(mock_llm)

    result = await core.execute_translation_step(
        {
            "content": "| Name | Value |\n| --- | --- |\n| alpha | one |",
            "meta_data": {
                "is_protected_block": True,
                "structure_kind": "markdown_table",
            },
        },
        {},
        {},
        max_api_retries=1,
    )

    assert result.success
    assert result.content.startswith("| 名称 | 值 |")
    assert "定向 fallback" in result.notes
    assert "原始注释" in result.notes
    assert result.new_terms_delta == []
    used_prompt = mock_llm.call_ai_model_api_async.await_args.args[0]
    assert "【定向 fallback 模式】" in used_prompt
    assert "markdown_table" in used_prompt
    mock_llm.rewrite_with_glossary_async.assert_not_awaited()

@pytest.mark.asyncio
async def test_targeted_fallback_activates_after_provider_structured_failure():
    mock_llm = MagicMock(spec=LLMService)
    mock_llm.provider = "kimi"
    mock_llm.create_prompt.return_value = "base prompt"
    error_response = {
        "origin_text": "{'translation': '半截结果', 'new_terms': [",
        "error": "Invalid JSON format",
    }
    success_response = {
        "translation": "恢复后的译文",
        "notes": "",
        "new_terms": [{"term": "foo", "translation": "条目", "reason": "sample"}],
    }
    mock_llm.call_ai_model_api_async = AsyncMock(side_effect=[
        (error_response, 30),
        (success_response, 25),
    ])
    mock_llm.repair_json_async = AsyncMock(return_value=(error_response, 10))
    mock_llm.rewrite_with_glossary_async = AsyncMock()

    core = TranslationCore(mock_llm)

    with patch("modules.translation_core.asyncio.sleep", new=AsyncMock()):
        result = await core.execute_translation_step(
            {"content": "Normal text", "meta_data": {}},
            {},
            {},
            repair_policy=RepairPolicy.NONE,
            max_api_retries=2,
        )

    assert result.success
    assert result.content == "恢复后的译文"
    assert "定向 fallback" in result.notes
    assert result.new_terms_delta == []
    assert mock_llm.call_ai_model_api_async.await_count == 2
    first_prompt = mock_llm.call_ai_model_api_async.await_args_list[0].args[0]
    second_prompt = mock_llm.call_ai_model_api_async.await_args_list[1].args[0]
    assert "【定向 fallback 模式】" not in first_prompt
    assert "【定向 fallback 模式】" in second_prompt
    assert "provider失败特征" in second_prompt
    mock_llm.rewrite_with_glossary_async.assert_not_awaited()
