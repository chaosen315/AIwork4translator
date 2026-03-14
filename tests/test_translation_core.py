import pytest
import asyncio
from unittest.mock import MagicMock
from modules.translation_core import TranslationCore, TranslationResult, TerminologyPolicy, RepairPolicy

@pytest.fixture
def mock_llm_service():
    service = MagicMock()
    # call_ai_model_api is called via to_thread, so it should be sync in mock
    service.create_prompt.return_value = "mock_prompt"
    service.call_ai_model_api.return_value = ({"translation": "T", "notes": "N", "new_terms": []}, 100)
    service.repair_json.return_value = ({"translation": "RT", "notes": "RN", "new_terms": []}, 50)
    service.rewrite_with_glossary.return_value = ({"translation": "RW", "notes": "RN", "new_terms": []}, 50)
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
    mock_llm_service.call_ai_model_api.assert_called_once()

@pytest.mark.asyncio
async def test_execute_translation_step_retry(mock_llm_service):
    # First call fails, second succeeds
    mock_llm_service.call_ai_model_api.side_effect = [Exception("Net Error"), ({"translation": "T2", "notes": "", "new_terms": []}, 50)]
    
    core = TranslationCore(mock_llm_service)
    result = await core.execute_translation_step({"content": "text", "meta_data": {}}, {}, {})
    
    assert result.success
    assert result.content == "T2"
    assert mock_llm_service.call_ai_model_api.call_count == 2

@pytest.mark.asyncio
async def test_json_repair(mock_llm_service):
    # API returns error dict
    mock_llm_service.call_ai_model_api.return_value = ({"error": "Invalid JSON", "origin_text": "bad json"}, 10)
    # Repair succeeds
    mock_llm_service.repair_json.return_value = ({"translation": "Fixed", "notes": "", "new_terms": []}, 50)
    
    core = TranslationCore(mock_llm_service)
    result = await core.execute_translation_step({"content": "text", "meta_data": {}}, {}, {})
    
    assert result.success
    assert result.content == "Fixed"
    mock_llm_service.repair_json.assert_called()

@pytest.mark.asyncio
async def test_rewrite_with_glossary(mock_llm_service):
    # API returns new term that conflicts
    mock_llm_service.call_ai_model_api.return_value = (
        {
            "translation": "Bad Term", 
            "notes": "", 
            "new_terms": [{"term": "foo", "translation": "bar"}]
        }, 10
    )
    
    # terms has 'foo' -> 'baz'
    # Use full dict structure for terms as per new changes
    terms = {"foo": {"term": "foo", "translation": "baz", "reason": "glossary"}}
    
    mock_llm_service.rewrite_with_glossary.return_value = (
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
    mock_llm_service.rewrite_with_glossary.assert_called_once()
    args = mock_llm_service.rewrite_with_glossary.call_args
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
