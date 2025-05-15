import csv,os,re
from typing import Dict
from nltk.stem import WordNetLemmatizer
from nltk.tokenize import word_tokenize
import nltk

# @title 模块3：验证csv文件格式，识别专业名词
def get_valid_path(filepath_prompt, validate_func):
    """获取有效的文件路径"""
    while True:
        path = input(filepath_prompt).strip()
        if validate_func(path):
            return path
        print(f"路径 {path} 不符合要求，请重新输入。")

def validate_csv_file(path):
    """验证CSV文件路径和内容"""
    # 检查文件是否存在
    if not os.path.exists(path):
        print("错误：文件不存在")
        return False

    # 检查文件是否是CSV格式
    if not path.lower().endswith('.csv'):
        print("错误：文件不是CSV格式")
        return False

    try:
        with open(path, 'r', encoding='utf-8-sig') as f:
            csv_reader = csv.reader(f)
            headers = next(csv_reader, None)  # 读取表头

            # 检查是否只有两列
            if headers is None or len(headers) != 2:
                print("错误：CSV文件必须包含两列")
                return False

            # 检查每一行是否非空
            for row_num, row in enumerate(csv_reader, start=2):  # 从第2行开始（表头是第1行）
                if len(row) != 2:
                    print(f"错误：第 {row_num} 行列数不等于2")
                    return False
                term, definition = row
                if not term.strip():
                    print(f"错误：第 {row_num} 行第一列（术语）为空")
                    return False
                if not definition.strip():
                    print(f"错误：第 {row_num} 行第二列（定义）为空")
                    return False
        return True
    except Exception as e:
        print(f"错误：读取CSV文件时出错：{e}")
        return False

# # 下载必要的NLTK数据
# nltk.download('punkt')
# nltk.download('wordnet')

# 修改后
nltk.data.path.append('/tmp/nltk_data')  # 添加临时路径
nltk.download('punkt', download_dir='/tmp/nltk_data')
nltk.download('punkt_tab', download_dir='/tmp/nltk_data')
nltk.download('wordnet', download_dir='/tmp/nltk_data')

def load_terms_dict(csv_file_path: str) -> Dict[str, str]:
    """
    从csv文件加载专业名词及其中文译名
    :param csv_file_path: csv文件路径
    :return: 专业名词字典 {英文术语: 中文译名}
    """
    terms_dict = {}
    with open(csv_file_path, 'r', encoding='utf-8') as file:
        reader = csv.reader(file)
        next(reader)  # 跳过表头（如果存在）
        for row in reader:
            if len(row) >= 2:  # 确保有英文和中文两列
                eng_term = row[0].strip()
                chi_term = row[1].strip()
                if eng_term:  # 忽略空键
                    terms_dict[eng_term] = chi_term
    return terms_dict

def filter_terms_dict(paragraph: str, terms_dict: Dict[str,str]) -> Dict[str, int]:
    """
    统计段落中专业名词出现次数
    :param paragraph: 段落内容
    :param terms_dict: 名词字典
    :return: 专业名词出现次数字典
    """
    return {
        term: trans
        for term, trans in terms_dict.items()
        if term.lower() in paragraph.lower()
    }

def preprocess_text(text: str) -> str:
    """
    预处理文本，包括词形还原等
    :param text: 输入文本
    :return: 预处理后的文本
    """
    lemmatizer = WordNetLemmatizer()
    tokens = word_tokenize(text)
    lemmatized_tokens = [lemmatizer.lemmatize(token) for token in tokens]
    return ' '.join(lemmatized_tokens)

def find_matching_terms(paragraph: str, terms_dict: Dict[str, str]) -> Dict[str, str]:
    """
    在段落中查找匹配的专业名词，并返回对应的中文译名
    :param paragraph: 段落内容
    :param terms_dict: 专业名词列表，包含英文和中文译名
    :return: 匹配到的专业名词及其中文译名
    """
    # 预处理段落文本
    processed_paragraph = preprocess_text(paragraph)
    print("processed paragraph:\n")
    print(processed_paragraph)

    # 创建匹配模式（考虑单词边界）
    term_patterns = {}
    for eng_term, chi_term in terms_dict.items():
        # 处理包含空格的术语
        escaped_term = re.escape(eng_term)
        pattern = r'\b{}\b'.format(escaped_term)
        term_patterns[pattern] = (eng_term, chi_term)
    print("term patterns:\n")
    # 查找匹配项
    matches = {}
    for pattern, (eng_term, chi_term) in term_patterns.items():
        if re.search(pattern, processed_paragraph, re.IGNORECASE):
            matches[eng_term] = chi_term
    print("matches:\n")
    print(matches)
    # 处理略写情况（部分匹配）
    for eng_term, chi_term in terms_dict.items():
        # 拆分术语为单词
        term_words = eng_term.split()
        if len(term_words) > 1:
            # 检查段落中是否包含术语的前几个单词
            found = True
            for word in term_words[:-1]:  # 至少匹配前n-1个单词
                if word.lower() not in processed_paragraph.lower():
                    found = False
                    break
            if found:
                matches[eng_term] = chi_term

    return matches