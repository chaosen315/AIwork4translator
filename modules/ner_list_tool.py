from transformers import pipeline
import pandas as pd
import torch
import os
from pathlib import Path
from datetime import datetime

class EntityRecognizer:
    ENTITY_MAPPING = {
        "PER": "人物",
        "ORG": "组织",
        "LOC": "地点",
        "MISC": "其他",
    }

    def __init__(self):
        self.target_name = "bert-large-cased-finetuned-conll03-english"
        self.model_path = self._find_model_directory()
        self.ner_pipeline = self._create_pipeline()

    def _find_model_directory(self):
        current_dir = Path(__file__).resolve().parent
        project_root = current_dir
        max_parents = 5
        while max_parents > 0 and project_root.parent != project_root:
            if (project_root / 'pyproject.toml').exists() or (project_root / 'requirements.txt').exists():
                break
            project_root = project_root.parent
            max_parents -= 1
        models_dir = project_root / 'models'
        if models_dir.exists() and models_dir.is_dir():
            for root, dirs, _ in os.walk(models_dir):
                for dir_name in dirs:
                    if self.target_name in dir_name:
                        return Path(root) / dir_name
        search_dirs = [current_dir, current_dir.parent, current_dir.parent.parent, project_root]
        for base_dir in search_dirs:
            for root, dirs, _ in os.walk(base_dir):
                for dir_name in dirs:
                    if self.target_name in dir_name:
                        return Path(root) / dir_name
        hardcoded_path = Path(project_root) / 'models' / 'dbmdz' / (self.target_name + '-for-ner')
        if hardcoded_path.exists():
            return hardcoded_path
        search_paths_str = "\n".join(str(d) for d in search_dirs)
        if models_dir.exists():
            search_paths_str += f"\n{models_dir}"
        raise FileNotFoundError(
            f"无法找到模型文件夹（包含'{self.target_name}'）。\n"
            f"搜索的路径包括：\n{search_paths_str}\n"
            f"也尝试了硬编码路径：{hardcoded_path}\n"
            "请确保模型文件已正确安装在项目的models目录下。"
        )

    def _create_pipeline(self):
        model_path_str = str(self.model_path)
        return pipeline(
            "ner",
            model=model_path_str,
            tokenizer=model_path_str,
            aggregation_strategy="simple",
            device=0 if torch.cuda.is_available() else -1,
        )

    @staticmethod
    def _subwords_check(results):
        merged = []
        current_entity = None
        for entity in results:
            if entity['word'].startswith('##'):
                if current_entity:
                    current_entity['word'] += entity['word'][2:]
                    current_entity['end'] = entity['end']
                    current_entity['score'] = (current_entity['score'] + entity['score']) / 2
            else:
                if current_entity:
                    merged.append(current_entity)
                current_entity = entity.copy()
                current_entity['entity_group'] = entity['entity_group']
        if current_entity:
            merged.append(current_entity)
        return merged

    @staticmethod
    def _merge_adjacent_entities(entities):
        if len(entities) < 2:
            return entities
        sorted_entities = sorted(entities, key=lambda x: x['start'])
        merged_entities = []
        i = 0
        while i < len(sorted_entities):
            current = sorted_entities[i]
            if i == len(sorted_entities) - 1:
                merged_entities.append(current)
                break
            next_entity = sorted_entities[i + 1]
            if current['end'] + 1 == next_entity['start']:
                merged_entity = {
                    'word': current['word'] + ' ' + next_entity['word'],
                    'score': (current['score'] + next_entity['score']) / 2,
                    'entity_group': current['entity_group'],
                    'start': current['start'],
                    'end': next_entity['end'],
                }
                merged_entities.append(merged_entity)
                i += 2
            else:
                merged_entities.append(current)
                i += 1
        return merged_entities

    def _process_texts(self, texts):
        results = self.ner_pipeline(texts, batch_size=32)
        entities_list = []
        for text_results in results:
            text_results = self._subwords_check(text_results)
            merged_results = self._merge_adjacent_entities(text_results)
            for entity in merged_results:
                entity_type = self.ENTITY_MAPPING.get(entity['entity_group'], entity['entity_group'])
                entities_list.append({
                    "原文": entity['word'],
                    "译文": "",
                    "名词类型": entity_type,
                })
        return entities_list

    @staticmethod
    def _load_in_chunks(file_path, chunk_size=32):
        with open(file_path, "r", encoding="utf-8") as f:
            chunk = []
            for line in f:
                cleaned_line = line.strip()
                if cleaned_line:
                    chunk.append(cleaned_line)
                    if len(chunk) == chunk_size:
                        yield chunk
                        chunk = []
            if chunk:
                yield chunk

    def process_file(self, file_path, output_file=None):
        path = Path(file_path).resolve()
        if not path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")
        if not path.is_file():
            raise ValueError(f"路径不是文件: {file_path}")
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M")
            output_file = path.with_name(f"{path.stem}_名词表_{timestamp}.csv")
        all_entities = []
        for chunk in self._load_in_chunks(file_path):
            chunk_results = self._process_texts(chunk)
            if chunk_results:
                all_entities.extend(chunk_results)
        if all_entities:
            df = pd.DataFrame(all_entities)
            df = df.drop_duplicates(subset=['原文'], keep='first')
            df.to_csv(output_file, index=False, encoding="utf_8_sig")
            print(f"成功保存 {len(df)} 个疑似专有名词到 {output_file}")
            return output_file
        print("未识别到任何可能的专有名词。")
        return None
