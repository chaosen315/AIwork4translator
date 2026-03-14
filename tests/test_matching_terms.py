import pytest
from modules.csv_process_tool import find_matching_terms

def test_single_word_with_optional_article():
    terms = {"priority": "优先级"}
    paragraph = "We discussed the priority of tasks yesterday."
    matches = find_matching_terms(paragraph, terms)
    assert matches == {"priority": "优先级"}

def test_multi_word_with_optional_article():
    terms = {"board game": "桌游"}
    paragraph = "He is learning the board game mechanics."
    matches = find_matching_terms(paragraph, terms)
    assert matches == {"board game": "桌游"}

def test_multi_word_exact_phrase_required():
    terms = {"board game": "桌游"}
    paragraph = "He mentioned the board but not the rules of the game."
    matches = find_matching_terms(paragraph, terms)
    assert matches == {}

def test_no_false_positive_on_substrings():
    terms = {"the": "冠词"}
    paragraph = "This theorem is complex."
    matches = find_matching_terms(paragraph, terms)
    assert matches == {}

def test_full_info_dict_support():
    """测试 regex 引擎下对全量信息字典的支持"""
    terms = {
        "priority": {"term": "priority", "translation": "优先级", "reason": "context"},
    }
    paragraph = "The priority is high."
    matches = find_matching_terms(paragraph, terms)
    
    assert "priority" in matches
    assert matches["priority"]["translation"] == "优先级"
    assert matches["priority"]["reason"] == "context"
