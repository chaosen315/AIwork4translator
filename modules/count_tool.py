import re
from markdown import markdown
from bs4 import BeautifulSoup
from modules.read_tool import read_structured_paragraphs

def count_md_words(file_path):
    with open(file_path,'r',encoding='utf-8') as f:
        md_content = f.read()
    html = markdown(md_content)
    soup = BeautifulSoup(html, 'html.parser')
    text = soup.get_text()
    words = re.findall(r'\b\w+\b', text)
    return len(words)

def count_structured_paragraphs(
    file_path: str,
    max_chunk_size: int = 600,
    min_chunk_size: int = 300,
    preserve_structure: bool = True
) -> int:
    paragraph_count = sum(
        1 for _ in read_structured_paragraphs(
            file_path,
            max_chunk_size=max_chunk_size,
            min_chunk_size=min_chunk_size,
            preserve_structure=preserve_structure,
        )
    )
    return max(1, paragraph_count)

def _find_split_position(line, remaining_space):
    if remaining_space >= len(line):
        return -1
    for pos in range(remaining_space, max(0, remaining_space-100), -1):
        if pos < len(line) and line[pos] in ('.', '。', '!', '！', '?', '？'):
            return pos + 1
    for pos in range(remaining_space, max(0, remaining_space-50), -1):
        if pos < len(line) and line[pos] in (',', '，', ';', '；'):
            return pos + 1
    for pos in range(remaining_space, max(0, remaining_space-20), -1):
        if pos < len(line) and line[pos].isspace():
            return pos + 1
    return remaining_space
