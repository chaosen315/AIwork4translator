from typing import Union, Tuple
import re
import json
import os

def write_to_markdown_through_json(
    json_file_path: str,
    output_md_path: str,
    p_id: int,
    content_info: dict,
    tracker_state: dict,
    mode: str = "structured"
) -> None:
    # 1. Update JSON
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: JSON file not found at {json_file_path}")
        return

    # Find and update
    target_idx = -1
    # Optimization: Check if index p_id-1 matches (assuming sorted 1-based IDs)
    if p_id - 1 < len(data['text_info']) and data['text_info'][p_id - 1]['paragraph_number'] == p_id:
        target_idx = p_id - 1
        item = data['text_info'][target_idx]
        item['translation'] = content_info.get('translation', '')
        item['notes'] = content_info.get('notes', '')
        item['new_terms'] = content_info.get('new_terms', [])
        item['status'] = 'completed'
    else:
        for idx, item in enumerate(data['text_info']):
            if item['paragraph_number'] == p_id:
                target_idx = idx
                item['translation'] = content_info.get('translation', '')
                item['notes'] = content_info.get('notes', '')
                item['new_terms'] = content_info.get('new_terms', [])
                item['status'] = 'completed'
                break
            
    if target_idx == -1:
        print(f"Error: Paragraph {p_id} not found in JSON")
        return
        
    with open(json_file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        
    # 2. Check and Write to MD
    while True:
        next_id = tracker_state['next_id']
        
        # Check if next_id exists
        if next_id - 1 >= len(data['text_info']):
            break
            
        candidate = data['text_info'][next_id - 1]
        
        # Double check ID match
        if candidate['paragraph_number'] != next_id:
             # Fallback search
             candidate = next((x for x in data['text_info'] if x['paragraph_number'] == next_id), None)
             if not candidate:
                 break
        
        if candidate.get('status') == 'completed':
            trans = candidate['translation']
            notes = candidate['notes']
            response = trans
            if notes:
                response = f"{trans}\n\n---\n\n{notes}\n\n---\n\n"
            
            write_to_markdown(output_md_path, (response, candidate['meta_data']), mode)
            
            tracker_state['next_id'] += 1
            # print(f"[System] 已写入段落 {next_id}") # Optional logging
        else:
            break

def write_to_markdown(
    output_file_path: str,
    content: Union[str, Tuple[str, dict]],
    mode: str = "flat"
) -> None:
    paragraph_text, metadata = _parse_content(content, mode)
    current_header = _find_last_header_in_file(output_file_path)
    with open(output_file_path, 'a', encoding='utf-8') as file:
        if metadata and mode != 'flat':
            # 结构化模式下，检查标题是否与当前文件中倒数第二个标题，即最后一个英文标题相同，如果相同，则只写入content，不写入标题
            header_path = metadata.get('header_path')
            if header_path and isinstance(header_path, list) and len(header_path) >= 2 and current_header == header_path[-2]:
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
