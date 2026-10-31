import os
import json
import asyncio
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from modules.read_tool import read_and_process_structured_paragraphs_to_json
from main import run_translation_loop
from modules.translation_core import TranslationCore, TranslationResult
from services.diagnostics import global_diagnostics

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
    mock_llm.call_ai_model_api_async = AsyncMock(return_value=(
        {
            "translation": "Translated Content", 
            "notes": "Some notes", 
            "new_terms": [{"term": "foo", "translation": "bar", "reason": "test"}]
        }, 
        100 # tokens
    ))
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
        assert mock_llm.call_ai_model_api_async.await_count == 2
        
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


@pytest.mark.asyncio
async def test_run_translation_loop_requeues_failed_segment_until_success(tmp_path):
    global_diagnostics.reset()

    fail_result = TranslationResult(
        content="",
        notes="",
        tokens=0,
        repair_tokens=0,
        new_terms_delta=[],
        matched_terms_delta=[],
        header_path=[],
        success=False,
        error="temporary failure",
    )
    success_result = TranslationResult(
        content="Recovered",
        notes="Recovered note",
        tokens=88,
        repair_tokens=0,
        new_terms_delta=[{"term": "retry", "translation": "重试", "reason": "test"}],
        matched_terms_delta=[],
        header_path=[],
        request_metadata={"request_id": "kimi-7", "prefix_hash": "retry-hash", "structured": True},
        success=True,
    )

    mock_core = MagicMock()
    mock_core.llm_service = MagicMock()
    mock_core.execute_translation_step = AsyncMock(side_effect=[fail_result, success_result])

    paragraphs = [
        {
            "paragraph_number": 1,
            "content": "Needs retry",
            "meta_data": {},
        }
    ]
    aggregated_new_terms = []
    output_md_file = str(tmp_path / "retry_success.md")

    with patch.dict(os.environ, {"PARAGRAPH_MAX_RETRIES": "1", "Currency_Limit": "1", "Requests_Per_Minute": "1"}), \
         patch("main.write_to_markdown") as mock_write, \
         patch("main.safe_api_diagnostics", new=AsyncMock()):
        total_tokens = await run_translation_loop(
            paragraphs,
            mock_core,
            {},
            aggregated_new_terms,
            output_md_file,
            PS=False,
        )

    assert total_tokens == 88
    assert mock_core.execute_translation_step.await_count == 2
    assert mock_write.call_count == 1
    assert aggregated_new_terms[0]["term"] == "retry"
    assert paragraphs[0]["status"] == "completed"
    assert "_paragraph_retry_count" not in paragraphs[0]


@pytest.mark.asyncio
async def test_run_translation_loop_collects_failed_segments_and_marks_partial(tmp_path):
    global_diagnostics.reset()

    fail_result = TranslationResult(
        content="",
        notes="",
        tokens=0,
        repair_tokens=0,
        new_terms_delta=[],
        matched_terms_delta=[],
        header_path=[],
        success=False,
        error="upstream timeout",
    )

    mock_core = MagicMock()
    mock_core.llm_service = MagicMock()
    mock_core.execute_translation_step = AsyncMock(side_effect=[fail_result, fail_result])

    json_path = tmp_path / "partial_intermediate.json"
    output_md_path = tmp_path / "partial.md"
    json_path.write_text(
        json.dumps(
            {
                "text_info": [
                    {
                        "paragraph_number": 7,
                        "content": "This paragraph keeps failing during translation.",
                        "translation": "",
                        "notes": "",
                        "new_terms": [],
                        "status": "pending",
                        "meta_data": {"header_path": ["# Chapter 1"]},
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    paragraphs = [
        {
            "paragraph_number": 7,
            "content": "This paragraph keeps failing during translation.",
            "meta_data": {"header_path": ["# Chapter 1"]},
        }
    ]

    with patch.dict(os.environ, {"PARAGRAPH_MAX_RETRIES": "1", "Currency_Limit": "1", "Requests_Per_Minute": "1"}), \
         patch("main.safe_api_diagnostics", new=AsyncMock()):
        total_tokens = await run_translation_loop(
            paragraphs,
            mock_core,
            {},
            [],
            str(output_md_path),
            PS=True,
            json_path=str(json_path),
        )

    assert total_tokens == 0
    assert mock_core.execute_translation_step.await_count == 2

    blueprint = json.loads(json_path.read_text(encoding="utf-8"))
    assert blueprint["translation_status"] == "partial"
    assert blueprint["failed_segments"][0]["paragraph_number"] == 7
    assert blueprint["failed_segments"][0]["retry_count"] == 2
    assert "upstream timeout" in blueprint["failed_segments"][0]["error_summary"]
    assert blueprint["text_info"][0]["status"] == "failed"

    output = output_md_path.read_text(encoding="utf-8")
    assert "当前翻译结果为部分完成" in output
    assert "未完成段落清单" in output
    assert "段落 7" in output

@pytest.mark.asyncio
async def test_run_translation_loop_preserves_targeted_fallback_result_in_finalize(tmp_path):
    global_diagnostics.reset()

    success_result = TranslationResult(
        content="| 名称 | 值 |\n| --- | --- |\n| alpha | one |",
        notes="注意：该段落触发定向 fallback，已切换到更保守的处理路径。",
        tokens=55,
        repair_tokens=0,
        new_terms_delta=[],
        matched_terms_delta=[{"term": "alpha", "translation": "阿尔法", "reason": "sample"}],
        header_path=["# Chapter 1"],
        request_metadata={"request_id": "kimi-3", "prefix_hash": "fallback-hash", "structured": True},
        success=True,
    )

    mock_core = MagicMock()
    mock_core.llm_service = MagicMock()
    mock_core.execute_translation_step = AsyncMock(return_value=success_result)

    json_path = tmp_path / "fallback_intermediate.json"
    output_md_path = tmp_path / "fallback.md"
    json_path.write_text(
        json.dumps(
            {
                "text_info": [
                    {
                        "paragraph_number": 3,
                        "content": "| Name | Value |\n| --- | --- |\n| alpha | one |",
                        "translation": "",
                        "notes": "",
                        "new_terms": [],
                        "status": "pending",
                        "meta_data": {
                            "header_path": ["# Chapter 1"],
                            "is_protected_block": True,
                            "structure_kind": "markdown_table",
                        },
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    paragraphs = [
        {
            "paragraph_number": 3,
            "content": "| Name | Value |\n| --- | --- |\n| alpha | one |",
            "meta_data": {
                "header_path": ["# Chapter 1"],
                "is_protected_block": True,
                "structure_kind": "markdown_table",
            },
        }
    ]

    with patch.dict(os.environ, {"Currency_Limit": "1", "Requests_Per_Minute": "1"}):
        total_tokens = await run_translation_loop(
            paragraphs,
            mock_core,
            {},
            [],
            str(output_md_path),
            PS=True,
            json_path=str(json_path),
        )

    assert total_tokens == 55
    blueprint = json.loads(json_path.read_text(encoding="utf-8"))
    assert blueprint["translation_status"] == "completed"
    assert blueprint["text_info"][0]["status"] == "completed"
    assert "定向 fallback" in blueprint["text_info"][0]["notes"]
    assert blueprint["text_info"][0]["request_metadata"]["request_id"] == "kimi-3"
    assert blueprint["text_info"][0]["prefix_hash"] == "fallback-hash"

    output = output_md_path.read_text(encoding="utf-8")
    assert "| 名称 | 值 |" in output
    assert "定向 fallback" in output

if __name__ == "__main__":
    # Manually run tests if executed directly (helper for dev)
    import sys
    sys.exit(pytest.main(["-v", __file__]))
