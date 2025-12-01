import re
from markdown import markdown
from bs4 import BeautifulSoup

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
    paragraph_count = 0
    if preserve_structure:
        current_chunk = []
        chunk_length = 0
        current_level = 0
        header_stack = []
        continuation_flag = False
        atx_header_pattern = re.compile(r'^(#{1,6})\s+(.+?)(\s+#+)?$')
        setext_header_pattern = re.compile(r'^={3,}$|^-{3,}$')
        with open(file_path, 'r', encoding='utf-8') as file:
            for line_num, line in enumerate(file, 1):
                line = line.rstrip('\n')
                raw_line = line
                stripped_line = line.strip()
                header_match = atx_header_pattern.match(line)
                setext_match = None
                if line_num > 1 and not stripped_line and setext_header_pattern.match(raw_line):
                    setext_match = True
                    header_level = 1 if '=' in raw_line else 2
                    if current_chunk:
                        prev_line_content = current_chunk[-1]
                        chunk_length -= len(prev_line_content) + 1
                        formatted_header = f"{'#' * header_level} {prev_line_content.strip()}"
                        chunk_length += len(formatted_header) + 1
                if header_match or setext_match:
                    if header_match:
                        header_level = len(header_match.group(1))
                    else:
                        header_level = 1 if '=' in raw_line else 2
                    should_count = False
                    if current_chunk:
                        if header_level <= current_level:
                            should_count = True
                        elif chunk_length + len(line) > max_chunk_size * 0.8:
                            should_count = True
                    if should_count:
                        paragraph_count += 1
                        current_chunk = []
                        chunk_length = 0
                        continuation_flag = False
                    current_level = header_level
                    while len(header_stack) >= current_level:
                        header_stack.pop()
                    if header_match:
                        header_text = header_match.group(2).strip()
                        formatted_header = f"{'#' * header_level} {header_text}"
                        header_stack.append(formatted_header)
                        current_chunk.append(line)
                        chunk_length += len(line) + 1
                    elif setext_match:
                        if current_chunk:
                            header_text = current_chunk.pop().strip()
                            formatted_header = f"{'#' * header_level} {header_text}"
                            header_stack.append(formatted_header)
                            current_chunk.append(formatted_header)
                            chunk_length = len(formatted_header) + 1
                    continuation_flag = False
                    continue
                if not stripped_line:
                    if current_chunk and not current_chunk[-1].endswith('\n\n'):
                        current_chunk.append('')
                        chunk_length += 1
                    continue
                line_length = len(line) + 1
                if chunk_length + line_length > max_chunk_size:
                    split_pos = _find_split_position(line, max_chunk_size - chunk_length)
                    if split_pos > 0:
                        paragraph_count += 1
                        chunk_length = len(line[split_pos:]) + 1
                        current_chunk = [line[split_pos:]]
                    else:
                        if current_chunk:
                            paragraph_count += 1
                        current_chunk = [line]
                        chunk_length = line_length
                    continuation_flag = True
                else:
                    current_chunk.append(line)
                    chunk_length += line_length
            if current_chunk:
                paragraph_count += 1
    else:
        pending_chunks = []
        pending_length = 0
        current_chunk = []
        current_length = 0
        with open(file_path, 'r', encoding='utf-8') as file:
            for line in file:
                line = line.rstrip('\n')
                stripped_line = line.strip()
                if not stripped_line:
                    if current_chunk:
                        chunk_text = '\n'.join(current_chunk)
                        current_chunk = []
                        current_length = 0
                        if len(chunk_text) < min_chunk_size:
                            pending_chunks.append(chunk_text)
                            pending_length += len(chunk_text)
                            if pending_length >= max_chunk_size:
                                paragraph_count += 1
                                pending_chunks = []
                                pending_length = 0
                        else:
                            if pending_chunks:
                                paragraph_count += 1
                                pending_chunks = []
                                pending_length = 0
                            paragraph_count += 1
                    continue
                line_length = len(line) + 1
                if current_length + line_length > max_chunk_size:
                    split_pos = _find_split_position(line, max_chunk_size - current_length)
                    if current_chunk:
                        chunk_text = '\n'.join(current_chunk)
                        if len(chunk_text) < min_chunk_size:
                            pending_chunks.append(chunk_text)
                            pending_length += len(chunk_text)
                            if pending_length >= max_chunk_size:
                                paragraph_count += 1
                                pending_chunks = []
                                pending_length = 0
                        else:
                            if pending_chunks:
                                paragraph_count += 1
                                pending_chunks = []
                                pending_length = 0
                            paragraph_count += 1
                    current_chunk = [line[split_pos:] if split_pos > 0 else line]
                    current_length = len(line[split_pos:]) if split_pos > 0 else line_length
                else:
                    current_chunk.append(line)
                    current_length += line_length
            if current_chunk:
                chunk_text = '\n'.join(current_chunk)
                if len(chunk_text) < min_chunk_size:
                    pending_chunks.append(chunk_text)
                    pending_length += len(chunk_text)
                else:
                    if pending_chunks:
                        paragraph_count += 1
                        pending_chunks = []
                        pending_length = 0
                    paragraph_count += 1
            if pending_chunks:
                paragraph_count += 1
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
