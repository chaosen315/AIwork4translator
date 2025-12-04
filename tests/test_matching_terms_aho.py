import os
import json
import pytest

from modules.csv_process_tool import find_matching_terms


@pytest.fixture(autouse=True)
def set_aho_engine(monkeypatch):
    monkeypatch.setenv('CSV_MATCH_ENGINE', 'aho')
    monkeypatch.setenv('CSV_MATCH_FUZZY', '0')


def test_aho_single_word_article_variants():
    terms = {"priority": "优先级"}
    assert find_matching_terms("We discussed the priority of tasks.", terms) == {"priority": "优先级"}
    assert find_matching_terms("This is a priority for the team.", terms) == {"priority": "优先级"}
    assert find_matching_terms("It became an priority unexpectedly.", terms) == {"priority": "优先级"}


def test_aho_multiword_with_article():
    terms = {"board game": "桌游"}
    assert find_matching_terms("He is learning the board game mechanics.", terms) == {"board game": "桌游"}


def test_aho_case_insensitive():
    terms = {"priority": "优先级"}
    assert find_matching_terms("The PRIORITY is high.", terms) == {"priority": "优先级"}


def test_aho_punctuation_boundaries():
    terms = {"priority": "优先级"}
    assert find_matching_terms("We discussed priority.", terms) == {"priority": "优先级"}


def test_aho_newline_boundary():
    terms = {"board game": "桌游"}
    assert find_matching_terms("We like the board game\nvery much.", terms) == {"board game": "桌游"}


def test_aho_no_substring_match():
    terms = {"the": "冠词"}
    assert find_matching_terms("This theorem is complex.", terms) == {}


def test_aho_no_hyphen_variation_for_phrase():
    terms = {"board game": "桌游"}
    assert find_matching_terms("We played the board-game yesterday.", terms) == {}


def test_aho_underscore_not_boundary():
    terms = {"priority": "优先级"}
    assert find_matching_terms("the_priority_is_set", terms) == {}


def test_aho_multiple_occurrences_collapsed():
    terms = {"priority": "优先级"}
    res = find_matching_terms("the priority and priority again", terms)
    assert res == {"priority": "优先级"}


def test_aho_fuzzy_off_by_default():
    terms = {"priority": "优先级"}
    assert find_matching_terms("We discussed prioritx today.", terms) == {}
