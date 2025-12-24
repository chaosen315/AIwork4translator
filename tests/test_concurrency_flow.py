import os
import json
import asyncio
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from modules.read_tool import read_and_process_structured_paragraphs_to_json
from main import run_translation_loop
from modules.translation_core import TranslationCore

# --- Tests for read_and_process_structured_paragraphs_to_json ---

def test_read_and_process_json_output(tmp_path):
    # 1. Setup a dummy markdown file
    md_content = """# Title
Paragraph 1 content is here.

## Section 1
Paragraph 2 is short.

Paragraph 3 is also short but should trigger merge.

Paragraph 4 is long enough to stand alone and stop the merge chain.
"""
    # Create file
    md_file = tmp_path / "test_input.md"
    md_file.write_text(md_content, encoding="utf-8")
    
    # 2. Call the function
    json_path = read_and_process_structured_paragraphs_to_json(
        str(md_file),
        max_chunk_size=1000,
        min_chunk_size=50, 
        preserve_structure=True
    )
    
    # 3. Verify JSON file existence
    assert os.path.exists(json_path)
    assert json_path.endswith("_intermediate.json")
    
    # 4. Verify Content
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    assert 'text_info' in data
    paragraphs = data['text_info']
    
    # Check structure
    for p in paragraphs:
        assert 'paragraph_number' in p
        assert 'meta_data' in p
        assert 'content' in p
        assert 'new_terms' in p

def test_short_paragraph_merging(tmp_path):
    md_content = """P1 is long enough to stay alone 1234567890.

P2 short.

P3 short.

P4 end.
"""
    md_file = tmp_path / "test_merge.md"
    md_file.write_text(md_content, encoding="utf-8")
    
    json_path = read_and_process_structured_paragraphs_to_json(
        str(md_file),
        max_chunk_size=1000,
        min_chunk_size=20,
        preserve_structure=False
    )
    
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    paragraphs = data['text_info']
    
    assert len(paragraphs) == 3
    assert "P1" in paragraphs[0]['content']
    assert "P2" in paragraphs[1]['content'] and "P3" in paragraphs[1]['content']
    assert "P4" in paragraphs[2]['content']


# --- Tests for run_translation_loop ---

@pytest.mark.asyncio
async def test_run_translation_loop_flow():
    # 1. Mock Objects
    mock_llm = MagicMock()
    # Mock call_ai_model_api to return valid result
    mock_llm.create_prompt.return_value = "prompt"
    mock_llm.call_ai_model_api.return_value = (
        {
            "translation": "Translated Content", 
            "notes": "Some notes", 
            "new_terms": [{"term": "foo", "translation": "bar", "reason": "test"}]
        }, 
        100 # tokens
    )
    mock_llm.repair_json.return_value = (
        {
            "translation": "Repaired Content", 
            "notes": "Repaired notes", 
            "new_terms": []
        },
        50
    )
    mock_llm.rewrite_with_glossary.return_value = (
        {
            "translation": "Rewritten Content", 
            "notes": "Rewritten notes", 
            "new_terms": []
        },
        50
    )
    
    core = TranslationCore(mock_llm)
    
    # Mock terms
    terms_dict = {}
    aggregated_new_terms = []
    
    # Mock output file
    output_md_file = "dummy_output.md"
    
    # Mock Paragraphs (Input from JSON)
    paragraphs = [
        {
            'paragraph_number': 1,
            'content': 'Paragraph 1',
            'meta_data': {'header_path': ['# H1']},
        },
        {
            'paragraph_number': 2,
            'content': 'Paragraph 2',
            'meta_data': {'header_path': ['# H1']},
        }
    ]
    
    # 2. Mock write_to_markdown (since it writes to disk)
    # We need to patch it where it is used in main.py
    with patch('main.write_to_markdown') as mock_write:
        # 3. Run the loop
        total_tokens = await run_translation_loop(
            paragraphs, 
            core, # Pass core
            terms_dict, 
            aggregated_new_terms, 
            output_md_file, 
            PS=True
        )
        
        # 4. Assertions
        assert total_tokens == 200 # 100 * 2
        
        # Check LLM calls
        assert mock_llm.call_ai_model_api.call_count == 2
        
        # Check Write calls
        assert mock_write.call_count == 2
        # Verify call arguments
        # args: (file_path, (response, meta), mode)
        call_args = mock_write.call_args_list[0]
        assert call_args[0][0] == output_md_file
        assert "Translated Content" in call_args[0][1][0]
        assert "Some notes" in call_args[0][1][0]
        assert call_args[0][2] == 'structured'
        
        # Check aggregated terms
        assert len(aggregated_new_terms) == 2
        assert aggregated_new_terms[0]['term'] == 'foo'

if __name__ == "__main__":
    # Manually run tests if executed directly (helper for dev)
    import sys
    sys.exit(pytest.main(["-v", __file__]))
