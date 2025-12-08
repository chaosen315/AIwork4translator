import os
import csv
import time

from modules.terminology_tool import save_glossary_df


def read_csv_rows(path):
    with open(path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        rows = list(reader)
    return rows


def test_save_glossary_df_preserves_basename_for_list(tmp_path, monkeypatch):
    original = tmp_path / "my_terms.csv"
    df = [
        {"term": "England", "translation": "英格兰"},
        {"term": "France", "translation": "法国"},
    ]
    out_path = save_glossary_df(df, str(original))

    assert os.path.exists(out_path)
    fname = os.path.basename(out_path)
    assert fname.startswith("my_terms_")
    assert fname.endswith(".csv")

    rows = read_csv_rows(out_path)
    assert rows[0] == ["term", "translation"]
    assert rows[1] == ["England", "英格兰"]
    assert rows[2] == ["France", "法国"]


def test_save_glossary_df_preserves_basename_for_xlsx(tmp_path):
    original = tmp_path / "glossary.xlsx"
    df = [
        {"term": "Board Game", "translation": "桌游"},
    ]
    out_path = save_glossary_df(df, str(original))
    assert os.path.exists(out_path)
    fname = os.path.basename(out_path)
    assert fname.startswith("glossary_")
    assert fname.endswith(".csv")


class DummyPd:
    class DataFrame:
        def __init__(self, rows):
            self._rows = rows

        def __getitem__(self, keys):
            if isinstance(keys, list):
                filtered = []
                for r in self._rows:
                    filtered.append({k: r.get(k, "") for k in keys})
                return DummyPd.DataFrame(filtered)
            raise TypeError("Unsupported key type")

        def to_csv(self, path, index=False, encoding="utf-8"):
            with open(path, "w", newline="", encoding=encoding) as f:
                writer = csv.writer(f)
                writer.writerow(["term", "translation"])
                for r in self._rows:
                    writer.writerow([r.get("term", ""), r.get("translation", "")])


def test_save_glossary_df_dataframe_branch_preserves_basename(tmp_path, monkeypatch):
    from modules import terminology_tool as tt

    monkeypatch.setattr(tt, "_try_import_pandas", lambda: DummyPd)

    original = tmp_path / "dict.csv"
    df = DummyPd.DataFrame([
        {"term": "Night City", "translation": "夜之城"},
    ])

    out_path = tt.save_glossary_df(df, str(original))
    assert os.path.exists(out_path)
    fname = os.path.basename(out_path)
    assert fname.startswith("dict_")
    assert fname.endswith(".csv")

    rows = read_csv_rows(out_path)
    assert rows[0] == ["term", "translation"]
    assert rows[1] == ["Night City", "夜之城"]

