from transformers import pipeline
import pandas as pd
import torch
import os
from pathlib import Path
from datetime import datetime
class EntityRecognizer:
    # 实体类型映射字典（类常量）
    ENTITY_MAPPING = {
        "PER": "人物",
        "ORG": "组织",
        "LOC": "地点",
        "MISC": "其他"
    }
    
    def __init__(self):
        self.target_name = "bert-large-cased-finetuned-conll03-english-for-ner"
        self.model_path = self._find_model_directory()
        self.ner_pipeline = self._create_pipeline()

    
    def _find_model_directory(self):
        """在最多两层父目录中搜索目标文件夹"""
        current_dir = Path(__file__).resolve().parent
        
        # 搜索范围：当前目录、父目录、祖父目录
        search_dirs = [
            current_dir,                # 第0层：当前目录
            current_dir.parent,         # 第1层：父目录
            current_dir.parent.parent   # 第2层：祖父目录
        ]
        
        # 在搜索范围内递归查找目标文件夹
        for base_dir in search_dirs:
            for root, dirs, _ in os.walk(base_dir):
                if self.target_name in dirs:
                    return Path(root) / self.target_name
        
        # 未找到时的处理
        raise FileNotFoundError(
            f"在以下目录中未找到模型文件夹 '{self.target_name}':\n" +
            "\n".join(str(d) for d in search_dirs)
        )
    
    def _create_pipeline(self):
        """创建NER pipeline"""
        model_path_str = str(self.model_path)
        return pipeline(
            "ner",
            model=model_path_str,
            tokenizer=model_path_str,
            aggregation_strategy="simple",
            device=0 if torch.cuda.is_available() else -1
        )
    
    @staticmethod
    def _subwords_check(results):
        """合并被分割的子词"""
        merged = []
        current_entity = None
        for entity in results:
            if entity['word'].startswith('##'):
                if current_entity:
                    # 合并子词
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
        """合并位置相邻且间隔单个空格的两个实体"""
        if len(entities) < 2:
            return entities
        
        # 按起始位置排序
        sorted_entities = sorted(entities, key=lambda x: x['start'])
        
        merged_entities = []
        i = 0
        
        while i < len(sorted_entities):
            current = sorted_entities[i]
            
            # 检查是否为最后一个实体
            if i == len(sorted_entities) - 1:
                merged_entities.append(current)
                break
            
            next_entity = sorted_entities[i + 1]
            
            # 检查是否相邻且间隔一个空格
            if current['end'] + 1 == next_entity['start']:
                
                # 创建合并实体
                merged_entity = {
                    'word': current['word'] + ' ' + next_entity['word'],
                    'score': (current['score'] + next_entity['score']) / 2,
                    'entity_group': current['entity_group'],
                    'start': current['start'],
                    'end': next_entity['end']
                }
                
                merged_entities.append(merged_entity)
                i += 2  # 跳过下一个实体（已合并）
            else:
                merged_entities.append(current)
                i += 1
        
        return merged_entities

    def _process_texts(self, texts):
        """处理文本块并提取实体"""
        results = self.ner_pipeline(texts, batch_size=32)
        
        entities_list = []
        for text_results in results:
            # 合并被分割的子词
            text_results = self._subwords_check(text_results)
            # 合并相邻实体
            merged_results = self._merge_adjacent_entities(text_results)
            
            for entity in merged_results:
                # 获取中文实体类型
                entity_type = self.ENTITY_MAPPING.get(
                    entity['entity_group'], 
                    entity['entity_group']
                )
                
                entities_list.append({
                    "原文": entity['word'],
                    "译文": "",
                    "名词类型": entity_type
                })
        
        return entities_list

    @staticmethod
    def _load_in_chunks(file_path, chunk_size=32):
        """生成器：分块读取大型文件"""
        with open(file_path, "r", encoding="utf-8") as f:
            chunk = []
            for line in f:
                cleaned_line = line.strip()
                if cleaned_line:
                    chunk.append(cleaned_line)
                    if len(chunk) == chunk_size:
                        yield chunk
                        chunk = []
            if chunk:  # 处理剩余的最后一块
                yield chunk

    def process_file(self, file_path, output_file=None):
        """处理整个文件并保存结果"""
        # 1. 验证文件路径合法性
        path = Path(file_path).resolve()
        if not path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")
        if not path.is_file():
            raise ValueError(f"路径不是文件: {file_path}")
        
        # 2. 动态设置输出文件名（与输入文件同目录）
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M")
            output_file = path.with_name(f"{path.stem}_名词表_{timestamp}.csv")
        else:
            output_file = Path(output_file)
        all_entities = []
        
        for chunk in self._load_in_chunks(file_path):
            chunk_results = self._process_texts(chunk)
            if chunk_results:
                all_entities.extend(chunk_results)
        
        # 整体去重并保存结果
        if all_entities:
            df = pd.DataFrame(all_entities)
            df = df.drop_duplicates(subset=['原文'], keep='first')
            df.to_csv(output_file, index=False, encoding="utf_8_sig")
            print(f"成功保存 {len(df)} 个疑似专有名词到 {output_file}")
            return output_file
        else:
            print("未识别到任何可能的专有名词。")
            return None

# 使用方法
# # 创建识别器实例
# recognizer = EntityRecognizer()

# # 处理文件
# result_file = recognizer.process_file("input.txt")

# # 如果需要处理多个文件
# for file_path in file_list:
#     recognizer.process_file(file_path, f"results/{Path(file_path).stem}_entities.csv")
