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
        if not normalized:
            return pd.DataFrame(columns=['term', 'translation', 'reason'])
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
        
        if 'reason' not in base.columns:
            base['reason'] = ''

        merged_terms = base[['term', 'translation', 'reason']].dropna(subset=['term', 'translation'])
        if isinstance(new_df, pd.DataFrame) and not new_df.empty:
            if 'reason' not in new_df.columns:
                new_df['reason'] = ''
            add_df = new_df[['term', 'translation', 'reason']].dropna(subset=['term', 'translation'])
            merged_terms = pd.concat([merged_terms, add_df], ignore_index=True)
        merged_terms = merged_terms.drop_duplicates(subset=['term'], keep='first')
        return merged_terms
    base_rows = []
    if isinstance(df, list):
        base_rows = [{'term': r.get('term', ''), 'translation': r.get('translation', ''), 'reason': r.get('reason', '')} for r in df]
    add_rows = [{'term': r.get('term', ''), 'translation': r.get('translation', ''), 'reason': r.get('reason', '')} for r in items]
    seen = set()
    result: List[Dict[str, Any]] = []
    for r in base_rows + add_rows:
        t = r.get('term', '')
        if t and t not in seen:
            seen.add(t)
            result.append(r)
    return result

def save_glossary_df(df, original_path: str) -> str:
    ts = time.strftime('%Y%m%d_%H%M%S')
    base_dir = os.path.dirname(os.path.abspath(original_path))
    original_name = os.path.splitext(os.path.basename(original_path))[0]
    out_path = os.path.join(base_dir, f'{original_name}_{ts}.csv')
    pd = _try_import_pandas()
    if pd and isinstance(df, pd.DataFrame):
        cols = ['term', 'translation']
        if 'reason' in df.columns:
            cols.append('reason')
        df[cols].to_csv(out_path, index=False, encoding='utf-8')
        return out_path
    with open(out_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        header = ['term', 'translation']
        has_reason = False
        if isinstance(df, list) and len(df) > 0 and 'reason' in df[0]:
            has_reason = True
            header.append('reason')
        writer.writerow(header)
        for r in df:
            row = [r.get('term', ''), r.get('translation', '')]
            if has_reason:
                row.append(r.get('reason', ''))
            writer.writerow(row)
    return out_path

def save_terms_result(merge_in_place: bool, glossary_df, aggregated_new_terms, original_path: str, blank_csv_path: str) -> str:
    if merge_in_place:
        merged_glossary = merge_new_terms(glossary_df, aggregated_new_terms)
        return save_glossary_df(merged_glossary, original_path)
    else:
        new_terms_df = dict_to_df(aggregated_new_terms)
        return save_glossary_df(new_terms_df, blank_csv_path)
