import os
import csv
import pytest

from modules.csv_process_tool import validate_csv_file


def write_csv(path, rows):
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        for r in rows:
            w.writerow(r)


def test_validate_csv_file_valid(tmp_path):
    p = tmp_path / "terms.csv"
    write_csv(p, [["term", "definition"], ["outlaw", "法外之徒"], ["priority", "优先级"]])
    ok, newp = validate_csv_file(str(p))
    assert ok is True
    assert newp == str(p)


def test_validate_csv_file_invalid_header_columns(tmp_path):
    p = tmp_path / "bad.csv"
    write_csv(p, [["only_one"], ["x"], ["y"]])
    ok, newp = validate_csv_file(str(p))
    assert ok is False
    assert newp == str(p)


def test_validate_csv_file_invalid_empty_cell(tmp_path):
    p = tmp_path / "empty.csv"
    write_csv(p, [["term", "definition"], ["", "法外之徒"]])
    ok, newp = validate_csv_file(str(p))
    assert ok is False
    assert newp == str(p)
