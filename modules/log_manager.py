import json
import os
from typing import Dict, List, Optional, Any

class TranslationLogManager:
    def __init__(self, blueprint_path: str):
        """
        Initialize the log manager.
        
        Args:
            blueprint_path: Path to the intermediate blueprint JSON file.
                            The log file will be named similarly but with .jsonl extension.
        """
        self.blueprint_path = blueprint_path
        self.log_path = self._get_log_path(blueprint_path)

    def _get_log_path(self, blueprint_path: str) -> str:
        """Derive the log file path from the blueprint path."""
        # e.g., data_intermediate.json -> data_translation_log.jsonl
        # or just side-by-side: data_intermediate.jsonl ?
        # The spec says "_translation_log.jsonl".
        # Let's try to match the directory and base name.
        directory = os.path.dirname(blueprint_path)
        filename = os.path.basename(blueprint_path)
        base_name = os.path.splitext(filename)[0]
        # if base_name ends with _intermediate, strip it for cleaner log name?
        # User spec: "A new _translation_log.jsonl file"
        # Let's keep it simple: replace .json with .jsonl or append _log.
        # If blueprint is "book_intermediate.json", log could be "book_translation_log.jsonl"
        if base_name.endswith('_intermediate'):
            base_name = base_name[:-13] # strip _intermediate
        
        return os.path.join(directory, f"{base_name}_translation_log.jsonl")

    def append_log(self, p_id: int, content_info: Dict[str, Any]) -> None:
        """
        Append a completed translation record to the log file.
        
        Args:
            p_id: Paragraph ID
            content_info: Dictionary containing translation, notes, etc.
        """
        record = {
            "id": p_id,
            "info": content_info,
            "status": "completed"
        }
        # Atomic append (OS guarantees atomicity for small appends, but even if not, 
        # distinct lines are usually safe enough for this purpose)
        with open(self.log_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(record, ensure_ascii=False) + '\n')

    def replay_logs(self) -> Dict[int, Dict[str, Any]]:
        """
        Read the log file and reconstruct the state of completed paragraphs.
        
        Returns:
            A dictionary mapping paragraph_id to its content_info.
        """
        completed_map = {}
        if not os.path.exists(self.log_path):
            return completed_map
            
        try:
            with open(self.log_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                        p_id = record.get("id")
                        info = record.get("info")
                        if p_id is not None and info:
                            completed_map[p_id] = info
                    except json.JSONDecodeError:
                        # Skip corrupted lines
                        continue
        except Exception as e:
            print(f"[Warning] Error replaying logs: {e}")
            
        return completed_map

    def get_preview_content(self, blueprint_data: Dict[str, Any]) -> str:
        """
        Generate a preview of the document content by merging blueprint data with logs.
        
        Args:
            blueprint_data: The loaded content of the blueprint JSON.
            
        Returns:
            A string containing the assembled Markdown content.
        """
        # Get latest updates from logs
        updates = self.replay_logs()
        
        # Merge and assemble
        preview_text = []
        text_info_list = blueprint_data.get('text_info', [])
        
        # Sort by paragraph_number just in case
        # Assuming text_info is already sorted or we rely on list order.
        # The main logic usually trusts the order in text_info.
        
        for item in text_info_list:
            p_id = item.get('paragraph_number')
            
            # Use updated info if available, otherwise use existing item info
            if p_id in updates:
                info = updates[p_id]
                translation = info.get('translation', '')
                notes = info.get('notes', '')
            else:
                translation = item.get('translation', '')
                notes = item.get('notes', '')
                
            # If not translated yet, what to show?
            # User wants "real-time preview".
            # Usually we show what's there. If empty, it's empty.
            # Or maybe show original?
            # For now, let's show the translation if it exists.
            
            if not translation:
                continue
                
            response = translation
            if notes:
                response = f"{translation}\n\n---\n\n{notes}"
            
            # Simple concatenation for preview
            # We might want to respect headers if we want a "structured" preview
            # But the requirement says "assembled text".
            # Let's try to include headers if they are in the blueprint item
            # But wait, blueprint item doesn't explicitly store "current header" in a simple way 
            # for reconstruction unless we look at 'header_path' in 'meta_data'.
            
            # For a quick preview, flat text is often enough, but let's try to be nice.
            # If we want to replicate write_to_markdown logic, it's complex.
            # Let's stick to a simple join for now, as the main output logic handles the complex structure.
            # Or better: check if we can reuse a formatter.
            
            preview_text.append(response)
            
        return "\n\n".join(preview_text)
