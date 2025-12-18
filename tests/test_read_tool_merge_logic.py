import pytest
from unittest.mock import patch
import json
import os
from modules.read_tool import read_and_process_structured_paragraphs_to_json

# Helper to create paragraph items as they appear in 'processed_items' inside the function
# But wait, 'read_structured_paragraphs' returns tuples: (content, metadata)
# The function then converts them to dicts.
# We are mocking 'read_structured_paragraphs', so we should return what it returns.

def make_raw_text(content):
    return (content, {'is_image': False})

def make_raw_img(desc="image"):
    return (f"![{desc}](url)", {'is_image': True})

@pytest.fixture
def mock_read_structured_paragraphs():
    with patch('modules.read_tool.read_structured_paragraphs') as mock:
        yield mock

def run_tool_and_get_result(mock_read, input_items, tmp_path, filename="test.md"):
    # Setup mock
    mock_read.return_value = input_items
    
    # Setup paths
    file_path = tmp_path / filename
    # Create a dummy file just in case the tool checks for existence (it doesn't seems to based on code reading, but good practice)
    file_path.write_text("dummy content", encoding='utf-8')
    
    # Run
    # min_chunk_size=100, max_chunk_size=200
    json_path = read_and_process_structured_paragraphs_to_json(
        str(file_path),
        max_chunk_size=200,
        min_chunk_size=100
    )
    
    # Read result
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    return data['text_info']

def test_merge_skip_images(mock_read_structured_paragraphs, tmp_path):
    """
    Test Feature 1 & 2: Skip images to merge text, and preserve image order.
    Scenario: Short Text -> Image -> Short Text
    Expected: Merged Text -> Image
    """
    items = [
        make_raw_text("Part A."),
        make_raw_img("Img1"),
        make_raw_text("Part B.")
    ]
    
    result = run_tool_and_get_result(mock_read_structured_paragraphs, items, tmp_path)
    
    assert len(result) == 2
    # Check text merge
    assert "Part A." in result[0]['content']
    assert "Part B." in result[0]['content']
    assert result[0]['meta_data']['is_image'] is False
    
    # Check image position
    assert result[1]['content'] == "![Img1](url)"
    assert result[1]['meta_data']['is_image'] is True

def test_consecutive_merge_with_multiple_skips(mock_read_structured_paragraphs, tmp_path):
    """
    Test Feature 3: Continuous merging across multiple images.
    Scenario: Short -> Image -> Short -> Image -> Short
    Expected: Merged(A+B+C) -> Image1 -> Image2
    """
    items = [
        make_raw_text("Part A."),
        make_raw_img("Img1"),
        make_raw_text("Part B."),
        make_raw_img("Img2"),
        make_raw_text("Part C.")
    ]
    
    result = run_tool_and_get_result(mock_read_structured_paragraphs, items, tmp_path)
    
    assert len(result) == 3
    # Merged Text
    assert "Part A." in result[0]['content']
    assert "Part B." in result[0]['content']
    assert "Part C." in result[0]['content']
    
    # Images
    assert "Img1" in result[1]['content']
    assert "Img2" in result[2]['content']

def test_sentence_break_merge(mock_read_structured_paragraphs, tmp_path):
    """
    Test Feature: Merge based on sentence break detection even if not short (but here we rely on logic).
    The logic is `can_merge = is_buffer_short or is_sentence_break`.
    Let's use texts that are LONG enough (>100) but have a break.
    """
    text_a = "A" * 110  # Long enough to NOT trigger is_buffer_short (min=100)
    # But it has no punctuation at end, suggesting a break? 
    # Wait, "A"*110 ends with 'A'. 
    # _is_sentence_midpage_break checks:
    # 1. tail_A not in punctuation -> True ('A')
    # 2. head_B starts with lower case -> True
    
    text_b = "and " + "b" * 50 + "." # Starts with lowercase and continuation word
    
    items = [
        make_raw_text(text_a),
        make_raw_text(text_b)
    ]
    
    result = run_tool_and_get_result(mock_read_structured_paragraphs, items, tmp_path)
    
    assert len(result) == 1
    assert text_a in result[0]['content']
    assert text_b in result[0]['content']

def test_robustness_end_with_image(mock_read_structured_paragraphs, tmp_path):
    """
    Test Feature 4: Robustness when list ends with image.
    Scenario: Short Text -> Image -> (End)
    Expected: Short Text -> Image (No merge possible)
    """
    items = [
        make_raw_text("Short text."),
        make_raw_img("ImgEnd")
    ]
    
    result = run_tool_and_get_result(mock_read_structured_paragraphs, items, tmp_path)
    
    assert len(result) == 2
    assert "Short text." in result[0]['content']
    assert "ImgEnd" in result[1]['content']

def test_robustness_consecutive_images(mock_read_structured_paragraphs, tmp_path):
    """
    Test Robustness: Consecutive images skipped.
    Scenario: Short Text -> Image -> Image -> Short Text
    Expected: Merged Text -> Image -> Image
    """
    items = [
        make_raw_text("Part A."),
        make_raw_img("Img1"),
        make_raw_img("Img2"),
        make_raw_text("Part B.")
    ]
    
    result = run_tool_and_get_result(mock_read_structured_paragraphs, items, tmp_path)
    
    assert len(result) == 3
    assert "Part A." in result[0]['content']
    assert "Part B." in result[0]['content']
    assert "Img1" in result[1]['content']
    assert "Img2" in result[2]['content']

def test_no_merge_if_too_long(mock_read_structured_paragraphs, tmp_path):
    """
    Test Limit: Don't merge if combined length exceeds max * 1.2
    max_chunk_size = 200. Limit = 240.
    Text A = 150 (Short? No, min=100. So is_buffer_short=False)
    Wait, if is_buffer_short is False, we check is_sentence_break.
    If is_sentence_break is False, no merge.
    
    Let's test "Short Text -> Image -> Long Text".
    Text A = 50 chars (Short)
    Text B = 300 chars.
    Combined = 350 > 240.
    Expected: Text A -> Image -> Text B
    """
    text_a = "A" * 50
    text_b = "B" * 300
    
    items = [
        make_raw_text(text_a),
        make_raw_img("Img1"),
        make_raw_text(text_b)
    ]
    
    result = run_tool_and_get_result(mock_read_structured_paragraphs, items, tmp_path)
    
    assert len(result) == 3
    assert len(result[0]['content']) == 50
    assert "Img1" in result[1]['content']
    assert len(result[2]['content']) == 300
