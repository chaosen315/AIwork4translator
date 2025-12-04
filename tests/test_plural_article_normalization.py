import os
import pytest

from modules.csv_process_tool import find_matching_terms


@pytest.fixture(autouse=True)
def use_aho_engine(monkeypatch):
    monkeypatch.setenv('CSV_MATCH_ENGINE', 'aho')
    monkeypatch.setenv('CSV_MATCH_FUZZY', '0')


def test_plural_text_matches_singular_term_with_article():
    terms = {"the Outlaw": "法外之徒"}
    paragraph = "A cell of Outlaws must pass a polygraph examination and interrogation."
    matches = find_matching_terms(paragraph, terms)
    assert matches == {"the Outlaw": "法外之徒"}


def test_plural_lowercase_text():
    terms = {"the Outlaw": "法外之徒"}
    paragraph = "a group of outlaws gathered."
    matches = find_matching_terms(paragraph, terms)
    assert matches == {"the Outlaw": "法外之徒"}


def test_article_removed_from_term_still_matches_without_article():
    terms = {"the Outlaw": "法外之徒"}
    paragraph = "They captured an outlaw yesterday."
    matches = find_matching_terms(paragraph, terms)
    assert matches == {"the Outlaw": "法外之徒"}
