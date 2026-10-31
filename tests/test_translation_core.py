import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from modules.translation_core import TranslationCore, TerminologyPolicy, RepairPolicy

@pytest.fixture
def mock_llm_service():
    service = MagicMock()
    service.create_prompt.return_value = "mock_prompt"
    service.last_prompt_metadata = {"request_id": "kimi-1", "prefix_hash": "abc123", "structured": True}
    service.call_ai_model_api_async = AsyncMock(return_value=({"translation": "T", "notes": "N", "new_terms": []}, 100))
    service.repair_json_async = AsyncMock(return_value=({"translation": "RT", "notes": "RN", "new_terms": []}, 50))
    service.rewrite_with_glossary_async = AsyncMock(return_value=({"translation": "RW", "notes": "RN", "new_terms": []}, 50))
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
    assert result.request_metadata["prefix_hash"] == "abc123"
    mock_llm_service.call_ai_model_api_async.assert_awaited_once()

@pytest.mark.asyncio
async def test_execute_translation_step_retry(mock_llm_service):
    # First call fails, second succeeds
    mock_llm_service.call_ai_model_api_async.side_effect = [Exception("Net Error"), ({"translation": "T2", "notes": "", "new_terms": []}, 50)]
    
    core = TranslationCore(mock_llm_service)
    with patch("modules.translation_core.asyncio.sleep", new=AsyncMock()):
        result = await core.execute_translation_step({"content": "text", "meta_data": {}}, {}, {})
    
    assert result.success
    assert result.content == "T2"
    assert mock_llm_service.call_ai_model_api_async.await_count == 2

@pytest.mark.asyncio
async def test_json_repair(mock_llm_service):
    # API returns error dict
    mock_llm_service.call_ai_model_api_async.return_value = ({"error": "Invalid JSON", "origin_text": "bad json"}, 10)
    # Repair succeeds
    mock_llm_service.repair_json_async.return_value = ({"translation": "Fixed", "notes": "", "new_terms": []}, 50)
    
    core = TranslationCore(mock_llm_service)
    result = await core.execute_translation_step({"content": "text", "meta_data": {}}, {}, {})
    
    assert result.success
    assert result.content == "Fixed"
    mock_llm_service.repair_json_async.assert_awaited()

@pytest.mark.asyncio
async def test_rewrite_with_glossary(mock_llm_service):
    # API returns new term that conflicts
    mock_llm_service.call_ai_model_api_async.return_value = (
        {
            "translation": "Bad Term", 
            "notes": "", 
            "new_terms": [{"term": "foo", "translation": "bar", "reason": "model output"}]
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
    mock_llm_service.rewrite_with_glossary_async.assert_awaited_once()
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

@pytest.mark.asyncio
async def test_partial_result_marks_incomplete_terms_and_notes(mock_llm_service):
    mock_llm_service.call_ai_model_api_async.return_value = (
        {
            "translation": "正文仍然有效",
            "notes": "原始注释",
            "new_terms": [{"term": "foo", "translation": "bar", "reason": "model output"}],
        },
        20,
    )
    mock_llm_service.rewrite_with_glossary_async.side_effect = RuntimeError("rewrite failed")

    core = TranslationCore(mock_llm_service)
    terms = {"foo": {"term": "foo", "translation": "baz", "reason": "glossary"}}

    with patch("modules.translation_core.asyncio.sleep", new=AsyncMock()):
        result = await core.execute_translation_step(
            {"content": "text", "meta_data": {}},
            terms,
            {},
            max_api_retries=1,
        )

    assert result.success
    assert result.content == "正文仍然有效"
    assert "术语/注释可能不完整，新术语未写入" in result.notes
    assert result.new_terms_delta == []
