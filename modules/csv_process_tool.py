import csv, os, re
from typing import Dict
from nltk.stem import WordNetLemmatizer
from nltk.tokenize import word_tokenize
import nltk

def get_valid_path(filepath_prompt, validate_func):
    while True:
        path = input(filepath_prompt).strip()
        # 智能去除双引号 - 处理用户输入时可能自带的引号
        path = path.strip('"\'')  # 去除开头和结尾的双引号和单引号
        is_valid, updated_path = validate_func(path)
        if is_valid:
            return updated_path
        print(f"路径 {path} 不符合要求，请重新输入。")

def validate_csv_file(path):
    """
    验证CSV文件格式，支持XLSX文件自动转换
    返回 (is_valid, updated_path) 元组
    """
    if not os.path.exists(path):
        print("错误：文件不存在")
        return False, path
    
    original_path = path
    converted_path = None
    
    # Handle XLSX files by converting them to CSV first
    if path.lower().endswith('.xlsx'):
        try:
            import pandas as pd
            # Convert XLSX to CSV
            converted_path = path.rsplit('.', 1)[0] + '_converted.csv'
            df = pd.read_excel(path)
            # Ensure the DataFrame has exactly 2 columns
            if len(df.columns) <= 2:
                print(f"错误：XLSX文件必须至少包含两列，当前有{len(df.columns)}列")
                return False, original_path
            # Rename columns to ensure consistent naming
            df.columns = ['term', 'definition']
            df.to_csv(converted_path, index=False, encoding='utf-8-sig')
            print(f"成功：XLSX文件已转换为CSV格式：{converted_path}")
            # Update path to use the converted CSV file
            path = converted_path
        except Exception as e:
            print(f"错误：转换XLSX文件时出错：{e}")
            return False, original_path
    elif not path.lower().endswith('.csv'):
        print("错误：文件不是CSV格式")
        return False, original_path
    
    try:
        with open(path, 'r', encoding='utf-8-sig') as f:
            csv_reader = csv.reader(f)
            headers = next(csv_reader, None)
            if headers is None or len(headers) != 2:
                print("错误：CSV文件必须包含两列")
                return False, original_path
            for row_num, row in enumerate(csv_reader, start=2):
                if len(row) != 2:
                    print(f"错误：第 {row_num} 行列数不等于2")
                    return False, original_path
                term, definition = row
                if not term.strip():
                    print(f"错误：第 {row_num} 行第一列（术语）为空")
                    return False, original_path
                if not definition.strip():
                    print(f"错误：第 {row_num} 行第二列（定义）为空")
                    return False, original_path
        return True, path
    except Exception as e:
        print(f"错误：读取CSV文件时出错：{e}")
        return False, original_path

nltk.data.path.append('/tmp/nltk_data')
nltk.download('punkt', download_dir='/tmp/nltk_data')
nltk.download('punkt_tab', download_dir='/tmp/nltk_data')
nltk.download('wordnet', download_dir='/tmp/nltk_data')

def load_terms_dict(csv_file_path: str) -> Dict[str, str]:
    terms_dict = {}
    with open(csv_file_path, 'r', encoding='utf-8') as file:
        reader = csv.reader(file)
        next(reader)
        for row in reader:
            if len(row) >= 2:
                eng_term = row[0].strip()
                chi_term = row[1].strip()
                if eng_term:
                    terms_dict[eng_term] = chi_term
    return terms_dict

def filter_terms_dict(paragraph: str, terms_dict: Dict[str,str]) -> Dict[str, int]:
    return {
        term: trans
        for term, trans in terms_dict.items()
        if term.lower() in paragraph.lower()
    }

def preprocess_text(text: str) -> str:
    lemmatizer = WordNetLemmatizer()
    tokens = word_tokenize(text)
    lemmatized_tokens = [lemmatizer.lemmatize(token) for token in tokens]
    return ' '.join(lemmatized_tokens)

def find_matching_terms(paragraph: str, terms_dict: Dict[str, str]) -> Dict[str, str]:
    processed_paragraph = preprocess_text(paragraph)
    term_patterns = {}
    for eng_term, chi_term in terms_dict.items():
        escaped_term = re.escape(eng_term)
        pattern = r'\b{}\b'.format(escaped_term)
        term_patterns[pattern] = (eng_term, chi_term)
    matches = {}
    for pattern, (eng_term, chi_term) in term_patterns.items():
        if re.search(pattern, processed_paragraph, re.IGNORECASE):
            matches[eng_term] = chi_term
    for eng_term, chi_term in terms_dict.items():
        term_words = eng_term.split()
        if len(term_words) > 1:
            found = True
            for word in term_words[:-1]:
                if word.lower() not in processed_paragraph.lower():
                    found = False
                    break
            if found:
                matches[eng_term] = chi_term
    return matches
