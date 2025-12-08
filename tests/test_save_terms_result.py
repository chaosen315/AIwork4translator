import os
import csv

from modules.terminology_tool import save_terms_result


def read_csv_rows(path):
    with open(path, 'r', encoding='utf-8') as f:
        return list(csv.reader(f))


def test_save_terms_result_merge_in_place_list_df(tmp_path):
    original = tmp_path / "terms.csv"
    glossary_df = [
        {"term": "England", "translation": "英格兰"},
        {"term": "France", "translation": "法国"},
    ]
    aggregated = [
        {"term": "England", "translation": "英格兰"},
        {"term": "Germany", "translation": "德国"},
    ]
    out_path = save_terms_result(True, glossary_df, aggregated, str(original), str(tmp_path / "unused.csv"))
    assert os.path.exists(out_path)
    fname = os.path.basename(out_path)
    assert fname.startswith("terms_")
    rows = read_csv_rows(out_path)
    assert rows[0] == ["term", "translation"]
    assert ["England", "英格兰"] in rows
    assert ["France", "法国"] in rows
    assert ["Germany", "德国"] in rows


def test_save_terms_result_new_glossary_path_list_df(tmp_path):
    original = tmp_path / "input.md"
    blank = tmp_path / "input_output_terminology.csv"
    aggregated = [
        {"term": "Board Game", "translation": "桌游"},
        {"term": "Card", "translation": "卡牌"},
    ]
    out_path = save_terms_result(False, [], aggregated, str(original), str(blank))
    assert os.path.exists(out_path)
    fname = os.path.basename(out_path)
    assert fname.startswith("input_output_terminology_")
    rows = read_csv_rows(out_path)
    assert rows[0] == ["term", "translation"]
    assert ["Board Game", "桌游"] in rows
    assert ["Card", "卡牌"] in rows

