import csv, os, re, time
from typing import Dict
from nltk.stem import WordNetLemmatizer
from nltk.tokenize import word_tokenize
import nltk

def get_valid_path(filepath_prompt, validate_func, default_path=None):
    while True:
        prompt = filepath_prompt
        if default_path:
            prompt = f"{filepath_prompt}上一次使用{default_path}，如继续使用请按回车，如有更换请输入地址："
        path = input(prompt).strip()
        if not path and default_path:
            path = default_path
        path = path.strip('"\'')
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
    try:
        tokens = word_tokenize(text)
    except Exception:
        tokens = re.findall(r"[A-Za-z]+|\d+|[^\sA-Za-z\d]", text)
    lemmatized_tokens = []
    for token in tokens:
        t = token.lower()
        if t.isalpha():
            try:
                r = lemmatizer.lemmatize(t, 'n')
                if r == t:
                    r = _to_singular(t)
                lemmatized_tokens.append(r)
            except Exception:
                lemmatized_tokens.append(_to_singular(t))
        else:
            lemmatized_tokens.append(t)
    return ' '.join(lemmatized_tokens)

def find_matching_terms(paragraph: str, terms_dict: Dict[str, str]) -> Dict[str, str]:
    t0 = time.perf_counter()
    processed_paragraph = preprocess_text(paragraph)
    lower_text = processed_paragraph.lower()
    matches = {}
    engine = os.getenv('CSV_MATCH_ENGINE', 'aho')
    if engine == 'aho':
        try:
            import ahocorasick
            A = ahocorasick.Automaton()
            for eng_term, chi_term in terms_dict.items():
                s = re.sub(r'^\s*(?:the|a|an)\s+', '', eng_term, flags=re.IGNORECASE)
                raw_base = re.sub(r'\s+', ' ', s).strip()
                base = raw_base.lower()
                if not base:
                    continue
                A.add_word(base, (eng_term, chi_term, len(base)))
                for art in ('the', 'a', 'an'):
                    w = f"{art} {base}"
                    A.add_word(w, (eng_term, chi_term, len(w)))
            A.make_automaton()
            for end_idx, val in A.iter(lower_text):
                eng_term, chi_term, mlen = val
                start_idx = end_idx - mlen + 1
                s = start_idx
                e = end_idx
                prev_c = lower_text[s-1] if s > 0 else ' '
                next_c = lower_text[e+1] if e+1 < len(lower_text) else ' '
                if not (prev_c.isalnum() or prev_c == '_') and not (next_c.isalnum() or next_c == '_'):
                    matches[eng_term] = chi_term
        except Exception:
            engine = 'regex'
    if engine == 'regex':
        optional_articles = r'(?:\b(?:the|a|an)\s+)?'
        for eng_term, chi_term in terms_dict.items():
            s = re.sub(r'^\s*(?:the|a|an)\s+', '', eng_term, flags=re.IGNORECASE)
            base = re.sub(r'\s+', ' ', s).strip().lower()
            if not base:
                continue
            escaped_base = re.escape(base)
            pattern = rf'{optional_articles}\b{escaped_base}\b'
            if re.search(pattern, lower_text, re.IGNORECASE):
                matches[eng_term] = chi_term
    if os.getenv('CSV_MATCH_FUZZY', '0') == '1':
        try:
            ed = int(os.getenv('CSV_MATCH_FUZZY_ED', '1'))
        except Exception:
            ed = 1
        tokens = lower_text.split()
        for eng_term, chi_term in terms_dict.items():
            if ' ' in eng_term:
                continue
            if eng_term in matches:
                continue
            t = eng_term.lower()
            for w in tokens:
                if _levenshtein_leq(t, w, ed):
                    matches[eng_term] = chi_term
                    break
    t1 = time.perf_counter()
    if os.getenv('CSV_MATCH_DEBUG') == '1':
        print(f'MATCH_TIME={t1 - t0:.6f}s MATCHES={len(matches)} TERMS={len(terms_dict)}')
    return matches

def _levenshtein_leq(a: str, b: str, k: int) -> bool:
    if a == b:
        return True
    if abs(len(a) - len(b)) > k:
        return False
    if k >= 2:
        return _lev(a, b) <= k
    if len(a) == len(b):
        diff = 0
        for i in range(len(a)):
            if a[i] != b[i]:
                diff += 1
                if diff > k:
                    return False
        return True
    if len(a) + 1 == len(b):
        i = j = 0
        diff = 0
        while i < len(a) and j < len(b):
            if a[i] == b[j]:
                i += 1
                j += 1
            else:
                diff += 1
                j += 1
                if diff > k:
                    return False
        return True
    if len(b) + 1 == len(a):
        i = j = 0
        diff = 0
        while i < len(a) and j < len(b):
            if a[i] == b[j]:
                i += 1
                j += 1
            else:
                diff += 1
                i += 1
                if diff > k:
                    return False
        return True
    return False

def _lev(a: str, b: str) -> int:
    n = len(a)
    m = len(b)
    dp = list(range(m + 1))
    for i in range(1, n + 1):
        prev = dp[0]
        dp[0] = i
        for j in range(1, m + 1):
            tmp = dp[j]
            cost = 0 if a[i - 1] == b[j - 1] else 1
            dp[j] = min(dp[j] + 1, dp[j - 1] + 1, prev + cost)
            prev = tmp
    return dp[m]

def _to_singular(t: str) -> str:
    if len(t) > 3 and t.endswith('ies'):
        return t[:-3] + 'y'
    if len(t) > 3 and t.endswith('es') and re.search(r'(s|sh|ch|x|z)es$', t):
        return t[:-2]
    if len(t) > 2 and t.endswith('s') and not t.endswith('ss') and not t.endswith('us'):
        return t[:-1]
    return t
