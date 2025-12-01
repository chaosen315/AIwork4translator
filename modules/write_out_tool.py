from typing import Union, Tuple
import re

def write_to_markdown(
    output_file_path: str,
    content: Union[str, Tuple[str, dict]],
    mode: str = "flat"
) -> None:
    paragraph_text, metadata = _parse_content(content, mode)
    current_header = _find_last_header_in_file(output_file_path)
    with open(output_file_path, 'a', encoding='utf-8') as file:
        if metadata and mode != 'flat':
            # 结构化模式下，检查标题是否与当前文件中最后一个标题相同，如果相同，则只写入content，不写入标题
            if current_header == metadata['header_path'][-1]:
                file.write(f"\n{paragraph_text}\n")
            else:
                _write_structured_section(file, paragraph_text, metadata)
        else:
            file.write(f"\n{paragraph_text}\n")

def _parse_content(content, mode) -> Tuple[str, dict]:
    if mode == 'flat':
        if isinstance(content, tuple):
            return content[0], None
        return content, None
    if mode == 'structured' and not isinstance(content, tuple):
        raise ValueError("结构化模式需要传入元组格式内容")
    if isinstance(content, tuple):
        return content[0], content[1]
    return content, None

def _write_structured_section(file, text: str, meta: dict):
    if not hasattr(file, '_header_stack'):
        file._header_stack = []
    current_headers = file._header_stack
    target_headers = meta['header_path']
    min_len = min(len(current_headers), len(target_headers))
    i = 0
    while i < min_len and current_headers[i] == target_headers[i]:
        i += 1
    file._header_stack = list(current_headers[:i])
    for header in target_headers[i:]:
        file.write(f"\n\n{header}\n\n")
        file._header_stack.append(header)
    file.write(f"{text}\n\n")

def _find_last_header_in_file(file_path: str):
    atx_pattern = re.compile(r'^(#{1,6})\s+(.+?)(\s+#+)?$')
    setext_pattern = re.compile(r'^={3,}$|^-{3,}$')
    header_stack = []
    last_header = None
    prev_line = None
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                raw_line = line.rstrip('\n')
                match = atx_pattern.match(raw_line)
                if match:
                    level = len(match.group(1))
                    text = match.group(2).strip()
                    while len(header_stack) >= level:
                        header_stack.pop()
                    header_stack.append(f"{'#' * level} {text}")
                    last_header = header_stack[-1]
                    prev_line = raw_line
                    continue
                if setext_pattern.match(raw_line) and prev_line:
                    level = 1 if raw_line.startswith('=') else 2
                    text = prev_line.strip()
                    while len(header_stack) >= level:
                        header_stack.pop()
                    header_stack.append(f"{'#' * level} {text}")
                    last_header = header_stack[-1]
                    continue
                prev_line = raw_line
    except FileNotFoundError:
        return None
    return last_header
