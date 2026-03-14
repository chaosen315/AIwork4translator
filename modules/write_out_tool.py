from typing import Union, Tuple, Optional
import re
import json
import os
from .log_manager import TranslationLogManager

def write_to_markdown_through_json(
    json_file_path: str,
    _output_md_path: str,
    p_id: int,
    content_info: dict,
    _tracker_state: dict,
    mode: str = "structured"
) -> None:
    """
    Appends the translation result to the incremental log file.
    Does NOT write to the Markdown file or the full JSON file to avoid I/O bottlenecks.

    _output_md_path and _tracker_state are kept for backward compatibility and are ignored.
    """
    log_manager = TranslationLogManager(json_file_path)
    log_manager.append_log(p_id, content_info)

def finalize_translation_output(
    json_file_path: str,
    output_md_path: str,
    mode: str = "structured"
) -> None:
    """
    Merges the incremental logs into the blueprint JSON and generates the final Markdown file.
    Should be called once at the end of the translation process.
    """
    # 1. Load Blueprint
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: JSON file not found at {json_file_path}")
        return

    # 2. Replay Logs
    log_manager = TranslationLogManager(json_file_path)
    updates = log_manager.replay_logs()
    
    if not updates:
        print("No translation logs found to merge.")
        return

    # 3. Update Blueprint in Memory
    text_info = data.get('text_info', [])
    # Create a map for faster lookup if needed, but iterating is fine for update
    # Better: iterate over text_info and update if p_id in updates
    
    # We also need to respect the order for MD writing
    # text_info is usually sorted by paragraph_number
    
    # Clear the file first to avoid appending to existing content?
    # write_to_markdown uses 'a' (append). So we should clear it if we are regenerating.
    with open(output_md_path, 'w', encoding='utf-8') as f:
        f.write('') # Clear file

    for item in text_info:
        p_id = item.get('paragraph_number')
        if p_id in updates:
            update = updates[p_id]
            # Update fields
            item['translation'] = update.get('translation', '')
            item['notes'] = update.get('notes', '')
            item['new_terms'] = update.get('new_terms', [])
            item['matched_terms'] = update.get('matched_terms', [])
            item['status'] = 'completed'
            
        # Write to MD if completed
        if item.get('status') == 'completed':
            trans = item.get('translation', '')
            notes = item.get('notes', '')
            response = trans
            if notes:
                response = f"{trans}\n\n---\n\n{notes}\n\n---\n\n"
            
            meta_data = item.get('meta_data')
            if meta_data and meta_data.get('is_continuation'):
                meta_data = None
                
            write_to_markdown(output_md_path, (response, meta_data), mode)

    # 4. Save Updated Blueprint
    with open(json_file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        
    # 5. Cleanup Log? 
    # Spec says: "TranslationLogManager is removed after successful finalization (or kept...)"
    # Let's keep it for safety or manual cleanup, or rename it.
    # For now, leaving it is safer. User can delete.
    if os.path.exists(log_manager.log_path):
        try:
            os.remove(log_manager.log_path)
            print(f"[System] Removed temporary log file: {log_manager.log_path}")
        except OSError as e:
            print(f"[Warning] Could not remove log file: {e}")

def write_to_markdown(
    output_file_path: str,
    content: Union[str, Tuple[str, Optional[dict]]],
    mode: str = "flat"
) -> None:
    paragraph_text, metadata = _parse_content(content, mode)
    # current_header = _find_last_header_in_file(output_file_path) # Removed as no longer needed for header check
    with open(output_file_path, 'a', encoding='utf-8') as file:
        if metadata and mode != 'flat':
            _write_structured_section(file, paragraph_text, metadata)
        else:
            file.write(f"\n{paragraph_text}\n")

def _parse_content(content, mode) -> Tuple[str, Optional[dict]]:
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
