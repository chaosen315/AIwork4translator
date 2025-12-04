import os
import pytest

from modules.csv_process_tool import get_valid_path


def test_get_valid_path_uses_default_when_empty(monkeypatch, tmp_path):
    default = str(tmp_path / "terms.csv")

    def validate(p):
        return True, p

    monkeypatch.setattr("builtins.input", lambda prompt: "")
    path = get_valid_path("请输入名词表CSV文件路径: ", validate, default)
    assert path == default


def test_get_valid_path_strips_quotes(monkeypatch):
    def validate(p):
        return True, p

    monkeypatch.setattr("builtins.input", lambda prompt: '"C:/data/terms.csv"')
    path = get_valid_path("请输入名词表CSV文件路径: ", validate)
    assert path == "C:/data/terms.csv"


def test_get_valid_path_retry_on_invalid(monkeypatch):
    inputs = iter(["C:/invalid.csv", "C:/valid.csv"])

    def validate(p):
        return (p.endswith("valid.csv")), p

    monkeypatch.setattr("builtins.input", lambda prompt: next(inputs))
    path = get_valid_path("请输入名词表CSV文件路径: ", validate)
    assert path.endswith("valid.csv")
