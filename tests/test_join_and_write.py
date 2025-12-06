import os
import tempfile
from modules.write_out_tool import write_to_markdown

def test_join_and_write_flat():
    translation = "正文一二三"
    notes = "- 术语A：说明\n- 术语B：说明"
    joined = "\n\n---\n\n".join([translation, notes])
    fd, path = tempfile.mkstemp(suffix='.md')
    os.close(fd)
    try:
        write_to_markdown(path, (joined, None), mode='flat')
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        assert '---' in content
        assert translation in content
        assert '- 术语A' in content
    finally:
        os.remove(path)
