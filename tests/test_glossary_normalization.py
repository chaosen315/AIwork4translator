from modules.csv_process_tool import normalize_terms_dict, serialize_terms_for_prompt


def test_normalize_terms_dict_stabilizes_duplicates_whitespace_and_punctuation():
    terms = {
        " Night   City ": {
            "term": " Night   City ",
            "translation": "夜之城",
            "reason": "赛博，朋克\r\n 固定译名 ",
        },
        "Night City": {
            "term": "Night City",
            "translation": " 夜之城 ",
            "reason": "赛博, 朋克\n固定译名",
        },
        "the Outlaw": {
            "term": "the Outlaw",
            "translation": " 法外之徒 ",
            "reason": "常见：阵营名",
        },
    }

    normalized = normalize_terms_dict(terms)

    assert normalized == [
        {
            "term": "Night City",
            "translation": "夜之城",
            "reason": "赛博, 朋克\n固定译名",
        },
        {
            "term": "the Outlaw",
            "translation": "法外之徒",
            "reason": "常见:阵营名",
        },
    ]


def test_serialize_terms_for_prompt_is_stable_for_semantically_equivalent_inputs():
    terms_a = {
        "the Outlaw": {"translation": "法外之徒", "reason": "常见：阵营名"},
        "Night  City": {"translation": " 夜之城 ", "reason": "赛博，朋克"},
        "Night City": {"translation": "夜之城", "reason": "赛博, 朋克"},
    }
    terms_b = {
        "Night City": {"translation": "夜之城", "reason": "赛博, 朋克"},
        "the Outlaw": {"translation": "法外之徒", "reason": "常见: 阵营名"},
    }

    assert serialize_terms_for_prompt(terms_a) == serialize_terms_for_prompt(terms_b)
    assert serialize_terms_for_prompt(terms_a) == "Night City -> 夜之城\nthe Outlaw -> 法外之徒"
