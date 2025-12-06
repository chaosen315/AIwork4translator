from modules.terminology_tool import merge_new_terms, dict_to_df

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

