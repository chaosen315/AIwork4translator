import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from modules.translation_core import TranslationCore, TranslationResult, TerminologyPolicy, RepairPolicy

@pytest.fixture
def mock_llm_service():
    service = MagicMock()
    # TranslationCore 通过 LLMService 的 *(_async) 方法调用模型（2026-03-14 异步化重构后），
    # mock 必须提供可 await 的异步接口，不能用同步 MagicMock。
    service.create_prompt.return_value = "mock_prompt"
    service.call_ai_model_api_async = AsyncMock(
        return_value=({"translation": "T", "notes": "N", "new_terms": []}, 100)
    )
    service.repair_json_async = AsyncMock(
        return_value=({"translation": "RT", "notes": "RN", "new_terms": []}, 50)
    )
    service.rewrite_with_glossary_async = AsyncMock(
        return_value=({"translation": "RW", "notes": "RN", "new_terms": []}, 50)
    )
    return service

@pytest.mark.asyncio
async def test_execute_translation_step_success(mock_llm_service):
    core = TranslationCore(mock_llm_service)
    segment = {"content": "text", "meta_data": {}}
    terms = {}
    new_terms = {}
    
    result = await core.execute_translation_step(segment, terms, new_terms)
    
    assert result.success
    assert result.content == "T"
    assert result.tokens == 100
    assert result.matched_terms_delta == []  # Check default empty list
    mock_llm_service.call_ai_model_api_async.assert_called_once()

@pytest.mark.asyncio
async def test_execute_translation_step_retry(mock_llm_service):
    # First call fails, second succeeds
    mock_llm_service.call_ai_model_api_async.side_effect = [
        Exception("Net Error"),
        ({"translation": "T2", "notes": "", "new_terms": []}, 50),
    ]
    
    core = TranslationCore(mock_llm_service)
    result = await core.execute_translation_step({"content": "text", "meta_data": {}}, {}, {})
    
    assert result.success
    assert result.content == "T2"
    assert mock_llm_service.call_ai_model_api_async.call_count == 2

@pytest.mark.asyncio
async def test_json_repair(mock_llm_service):
    # API returns error dict
    mock_llm_service.call_ai_model_api_async.return_value = (
        {"error": "Invalid JSON", "origin_text": "bad json"},
        10,
    )
    # Repair succeeds
    mock_llm_service.repair_json_async.return_value = (
        {"translation": "Fixed", "notes": "", "new_terms": []},
        50,
    )
    
    core = TranslationCore(mock_llm_service)
    result = await core.execute_translation_step({"content": "text", "meta_data": {}}, {}, {})
    
    assert result.success
    assert result.content == "Fixed"
    mock_llm_service.repair_json_async.assert_called()

@pytest.mark.asyncio
async def test_rewrite_with_glossary(mock_llm_service):
    # API returns new term that conflicts
    mock_llm_service.call_ai_model_api_async.return_value = (
        {
            "translation": "Bad Term", 
            "notes": "", 
            "new_terms": [{"term": "foo", "translation": "bar"}]
        }, 10
    )
    
    # terms has 'foo' -> 'baz'
    # Use full dict structure for terms as per new changes
    terms = {"foo": {"term": "foo", "translation": "baz", "reason": "glossary"}}
    
    mock_llm_service.rewrite_with_glossary_async.return_value = (
        {
            "translation": "Good Term",
            "notes": "",
            "new_terms": []
        }, 50
    )
    
    core = TranslationCore(mock_llm_service)
    result = await core.execute_translation_step({"content": "text", "meta_data": {}}, terms, {})
    
    assert result.success
    assert result.content == "Good Term"
    # Ensure rewrite was called with corrections
    mock_llm_service.rewrite_with_glossary_async.assert_called_once()
    args = mock_llm_service.rewrite_with_glossary_async.call_args
    # args[0] is (translation, notes, corrections)
    # corrections should be simple dict {term: translation}
    assert args[0][2] == {"foo": "baz"}

@pytest.mark.asyncio
async def test_matched_terms_delta(mock_llm_service):
    """Test that matched_terms_delta is correctly populated from terms"""
    core = TranslationCore(mock_llm_service)
    segment = {"content": "The priority is high.", "meta_data": {}}
    
    # Prepare terms dict with full info
    terms = {
        "priority": {"term": "priority", "translation": "优先级", "reason": "context"}
    }
    new_terms = {}
    
    result = await core.execute_translation_step(segment, terms, new_terms)
    
    assert result.success
    # Check if matched_terms_delta contains the expected term info
    assert len(result.matched_terms_delta) == 1
    matched = result.matched_terms_delta[0]
    assert matched["term"] == "priority"
    assert matched["translation"] == "优先级"
    assert matched["reason"] == "context"
