import re
from markdown import markdown
from bs4 import BeautifulSoup

def count_md_words(file_path):
    with open(file_path,'r',encoding='utf-8') as f:
        md_content = f.read()
    html = markdown(md_content)
    soup = BeautifulSoup(html, 'html.parser')
    text = soup.get_text()
    words = re.findall(r'\b\w+\b', text)
    return len(words)