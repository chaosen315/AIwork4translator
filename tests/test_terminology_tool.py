from modules.terminology_tool import merge_new_terms, dict_to_df, save_glossary_df
import pandas as pd
import os

def test_merge_deduplicate_prefers_existing():
    # 基础表含已有译名
    base = dict_to_df([
        {"term": "Night City", "translation": "夜之城", "reason": ""},
        {"term": "Cyberpunk", "translation": "赛博朋克", "reason": ""},
    ])
    # 新术语尝试覆盖，但应保留已有译名
    incoming = [
        {"term": "Night City", "translation": "夜城", "reason": "别名"},
        {"term": "V", "translation": "V", "reason": "人名"},
    ]
    merged = merge_new_terms(base, incoming)
    # merged 可能是DataFrame或list
    def get_rows(m):
        try:
            return m.to_dict(orient='records')
        except Exception:
            return m
    rows = get_rows(merged)
    d = {r['term']: r['translation'] for r in rows}
    assert d.get('Night City') == '夜之城'
    assert d.get('V') == 'V'

def test_merge_adds_reason_column_if_missing():
    # Base dataframe without reason column
    base_data = [
        {"term": "Apple", "translation": "苹果"},
        {"term": "Banana", "translation": "香蕉"}
    ]
    base = pd.DataFrame(base_data)
    
    # New items with reason
    items = [
        {"term": "Cherry", "translation": "樱桃", "reason": "Fruit"},
        {"term": "Apple", "translation": "苹果New", "reason": "Ignored"} # Should be duplicate
    ]
    
    merged = merge_new_terms(base, items)
    
    assert 'reason' in merged.columns
    assert len(merged) == 3
    
    # Check content
    rows = merged.set_index('term').to_dict('index')
    
    # Existing term should preserve original data, and have empty reason (since base didn't have reason)
    assert rows['Apple']['translation'] == '苹果'
    assert rows['Apple']['reason'] == '' or pd.isna(rows['Apple']['reason'])
    
    # New term should have reason
    assert rows['Cherry']['translation'] == '樱桃'
    assert rows['Cherry']['reason'] == 'Fruit'

def test_merge_preserves_existing_reason():
    # Base dataframe with reason column
    base_data = [
        {"term": "Dog", "translation": "狗", "reason": "Animal"},
    ]
    base = pd.DataFrame(base_data)
    
    items = [
        {"term": "Cat", "translation": "猫", "reason": "Pet"},
    ]
    
    merged = merge_new_terms(base, items)
    
    assert 'reason' in merged.columns
    rows = merged.set_index('term').to_dict('index')
    
    assert rows['Dog']['reason'] == 'Animal'
    assert rows['Cat']['reason'] == 'Pet'

def test_save_glossary_includes_reason(tmp_path):
    df = pd.DataFrame([
        {"term": "Test", "translation": "测试", "reason": "Just a test"}
    ])
    
    # Create a dummy file to simulate original path
    original_path = tmp_path / "glossary.csv"
    original_path.touch()
    
    saved_path = save_glossary_df(df, str(original_path))
    
    assert os.path.exists(saved_path)
    
    # Read back to verify
    saved_df = pd.read_csv(saved_path)
    assert 'reason' in saved_df.columns
    assert saved_df.iloc[0]['reason'] == 'Just a test'

