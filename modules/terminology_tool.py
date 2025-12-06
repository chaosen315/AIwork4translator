import os
import csv
import time
from typing import List, Dict, Any

def _try_import_pandas():
    try:
        import pandas as pd
        return pd
    except Exception:
        return None

def load_glossary_df(path: str):
    pd = _try_import_pandas()
    if pd:
        if path.lower().endswith('.xlsx'):
            df = pd.read_excel(path)
        else:
            df = pd.read_csv(path, encoding='utf-8')
        cols = list(df.columns)
        if len(cols) >= 2:
            df = df.rename(columns={cols[0]: 'term', cols[1]: 'translation'})
        else:
            df = pd.DataFrame(columns=['term', 'translation'])
        return df
    rows: List[Dict[str, Any]] = []
    if path.lower().endswith('.csv'):
        with open(path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            header = next(reader, None)
            for row in reader:
                if len(row) >= 2:
                    rows.append({'term': row[0].strip(), 'translation': row[1].strip()})
    return rows

def dict_to_df(items: List[Dict[str, Any]]):
    pd = _try_import_pandas()
    normalized = [normalize_keys(x) for x in items]
    if pd:
        return pd.DataFrame(normalized)
    return normalized

def normalize_keys(item: Dict[str, Any]) -> Dict[str, Any]:
    return {
        'term': str(item.get('term', '')),
        'translation': str(item.get('translation', '')),
        'reason': str(item.get('reason', '')),
    }

def merge_new_terms(df, items: List[Dict[str, Any]]):
    pd = _try_import_pandas()
    new_df = dict_to_df(items)
    if pd and isinstance(df, pd.DataFrame):
        base = df.copy()
        if 'term' not in base.columns or 'translation' not in base.columns:
            base = base.rename(columns={list(base.columns)[0]: 'term', list(base.columns)[1]: 'translation'})
        merged_terms = base[['term', 'translation']].dropna()
        if isinstance(new_df, pd.DataFrame) and not new_df.empty:
            add_df = new_df[['term', 'translation']].dropna()
            merged_terms = pd.concat([merged_terms, add_df], ignore_index=True)
        merged_terms = merged_terms.drop_duplicates(subset=['term'], keep='first')
        return merged_terms
    base_rows = []
    if isinstance(df, list):
        base_rows = [{'term': r.get('term', ''), 'translation': r.get('translation', '')} for r in df]
    add_rows = [{'term': r.get('term', ''), 'translation': r.get('translation', '')} for r in items]
    seen = set()
    result: List[Dict[str, Any]] = []
    for r in base_rows + add_rows:
        t = r.get('term', '')
        if t and t not in seen:
            seen.add(t)
            result.append({'term': r.get('term', ''), 'translation': r.get('translation', '')})
    return result

def save_glossary_df(df, original_path: str) -> str:
    ts = time.strftime('%Y%m%d_%H%M%S')
    base_dir = os.path.dirname(os.path.abspath(original_path))
    out_path = os.path.join(base_dir, f'glossary_{ts}.csv')
    pd = _try_import_pandas()
    if pd and isinstance(df, pd.DataFrame):
        df[['term', 'translation']].to_csv(out_path, index=False, encoding='utf-8')
        return out_path
    with open(out_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['term', 'translation'])
        for r in df:
            writer.writerow([r.get('term', ''), r.get('translation', '')])
    return out_path
