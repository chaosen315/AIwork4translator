
import pytest
import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unittest.mock import MagicMock, patch
from main import run_translation_loop

@pytest.mark.asyncio
async def test_replay_restores_aggregated_terms():
    # Mock TranslationCore
    mock_core = MagicMock()
    mock_core.llm_service = MagicMock()
    
    # Mock LogManager
    mock_log_manager = MagicMock()
    updates = {
        1: {
            'translation': 'bar', 
            'notes': 'note',
            'new_terms': [{'term': 'foo', 'translation': 'bar'}]
        }
    }
    mock_log_manager.replay_logs.return_value = updates
    
    # Setup inputs
    paragraphs = [{'paragraph_number': 1, 'content': 'foo'}]
    terms_dict = {}
    aggregated_new_terms = []
    output_md_file = "dummy_output.md"
    PS = False
    json_path = "dummy_log.json"
    
    # Patch TranslationLogManager in main.py
    with patch('main.TranslationLogManager', return_value=mock_log_manager):
        # Patch asyncio.to_thread to run synchronously for the test
        # or let it run since replay_logs is mocked
        # The original code uses await asyncio.to_thread(log_manager.replay_logs)
        # So we just need log_manager.replay_logs to return the dict
        
        # We also need to mock write_to_markdown_through_json to avoid file I/O errors if any worker runs
        # But here, paragraph 1 is completed, so queue should be empty.
        
        await run_translation_loop(
            paragraphs, 
            mock_core, 
            terms_dict, 
            aggregated_new_terms, 
            output_md_file, 
            PS, 
            json_path
        )
        
    # Assertions
    # 1. Check if paragraph status is updated
    assert paragraphs[0]['status'] == 'completed'
    assert paragraphs[0]['translation'] == 'bar'
    
    # 2. Check if aggregated_new_terms is updated (The Fix)
    assert len(aggregated_new_terms) == 1
    assert aggregated_new_terms[0]['term'] == 'foo'
    assert aggregated_new_terms[0]['translation'] == 'bar'
