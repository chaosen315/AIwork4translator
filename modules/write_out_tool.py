from typing import Union, Tuple, Optional, List, Dict, Any
import re
import json
import os
from .log_manager import TranslationLogManager


def _write_partial_completion_notice(
    output_md_path: str,
    failed_segments: List[Dict[str, Any]],
    total_paragraphs: int,
) -> None:
    """在最终 Markdown 顶部写入“部分完成”摘要，便于用户立即看到失败段信息。"""
    completed_count = max(total_paragraphs - len(failed_segments), 0)
    failed_ids = [str(item.get('paragraph_number', '?')) for item in failed_segments]

    with open(output_md_path, 'w', encoding='utf-8') as f:
        f.write("> [!WARNING]\n")
        f.write("> 当前翻译结果为部分完成。\n")
        f.write(f"> 已完成段落：{completed_count}/{total_paragraphs}\n")
        f.write(f"> 未完成段落：{', '.join(failed_ids) if failed_ids else '无'}\n\n")
        f.write("## 未完成段落清单\n\n")

        if not failed_segments:
            f.write("- 无\n\n")
            return

        for item in failed_segments:
            p_id = item.get('paragraph_number', '?')
            retry_count = item.get('retry_count', '?')
            error_summary = item.get('error_summary', '未知错误')
            header_path = " > ".join(item.get('header_path', []) or [])
            content_preview = item.get('content_preview', '')

            f.write(f"- 段落 {p_id}：重试 {retry_count} 次后仍失败；错误：{error_summary}\n")
            if header_path:
                f.write(f"  标题路径：{header_path}\n")
            if content_preview:
                f.write(f"  上下文：{content_preview}\n")
        f.write("\n---\n")

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
    mode: str = "structured",
    failed_segments: Optional[List[Dict[str, Any]]] = None,
) -> None:
    """
    将增量日志回放到蓝图 JSON，并统一生成最终 Markdown。
    若存在失败段，则同时写入“部分完成”摘要，并把失败清单回写到 `_intermediate.json`。
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
    
    # 3. 在内存中更新蓝图，并将失败段状态同步回 JSON。
    text_info = data.get('text_info', [])
    total_paragraphs = len(text_info)
    failed_segments = failed_segments if failed_segments is not None else data.get('failed_segments', [])
    failure_map = {
        item.get('paragraph_number'): item
        for item in failed_segments
        if item.get('paragraph_number') is not None
    }
    # Create a map for faster lookup if needed, but iterating is fine for update
    # Better: iterate over text_info and update if p_id in updates
    
    # We also need to respect the order for MD writing
    # text_info is usually sorted by paragraph_number
    
    # 先清空或写入部分完成提示，避免与旧 Markdown 内容叠加。
    if failed_segments:
        _write_partial_completion_notice(output_md_path, failed_segments, total_paragraphs)
    else:
        with open(output_md_path, 'w', encoding='utf-8') as f:
            f.write('')

    for item in text_info:
        p_id = item.get('paragraph_number')
        if p_id in updates:
            update = updates[p_id]
            # Update fields
            item['translation'] = update.get('translation', '')
            item['notes'] = update.get('notes', '')
            item['new_terms'] = update.get('new_terms', [])
            item['matched_terms'] = update.get('matched_terms', [])
            item['request_metadata'] = update.get('request_metadata', {})
            item['prefix_hash'] = update.get('prefix_hash') or item.get('request_metadata', {}).get('prefix_hash', '')
            item['status'] = 'completed'
            item.pop('failure_info', None)
        elif p_id in failure_map:
            item['status'] = 'failed'
            item['failure_info'] = failure_map[p_id]
            
        # 仅已完成段会被写入最终 Markdown；失败段只出现在顶部摘要中。
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
    data['failed_segments'] = failed_segments
    data['translation_status'] = 'partial' if failed_segments else 'completed'
    data['completed_paragraphs'] = sum(1 for item in text_info if item.get('status') == 'completed')
    data['total_paragraphs'] = total_paragraphs

    with open(json_file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        
    # 5. 合并完成后删除临时日志，避免后续恢复时误把旧日志再次回放。
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
