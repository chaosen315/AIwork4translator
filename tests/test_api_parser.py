import json
import pytest
from modules.api_tool import parse_translation_response, translation_json_schema

def test_parse_valid_json():
    payload = {
        "translation": "中文正文",
        "notes": "- 术语1：理由",
        "newterminology": [
            {"term": "Night City", "translation": "夜之城", "reason": "固定译名"}
        ]
    }
    text = json.dumps(payload, ensure_ascii=False)
    result = parse_translation_response(text)
    assert result["translation"] == "中文正文"
    assert result["notes"].startswith("-")
    assert isinstance(result["newterminology"], list)
    assert result["newterminology"][0]["term"] == "Night City"

def test_parse_text_fallback_raises():
    text = "纯文本输出，不是JSON"
    with pytest.raises(Exception):
        parse_translation_response(text)

def test_parse_partial_json_in_text():
    json_block = json.dumps({
        "translation": "中文",
        "notes": "- 说明",
        "newterminology": []
    }, ensure_ascii=False)
    text = "前缀\n" + json_block + "\n后缀"
    result = parse_translation_response(text)
    assert result["translation"] == "中文"
    assert result["notes"].startswith("-")

def test_schema_shape():
    schema = translation_json_schema()
    props = schema.get("properties", {})
    assert set(["translation", "notes", "newterminology"]).issubset(props.keys())
