text = """1d10

Your Mystery Box

1d6

Inside the Box is...

1

2

3

4

5

6

7

8

9

A box bound tightly in rope

A box covered in chipped paint

A box dripping wet with fluid

A box freezing cold to the touch

A box handsomely gift wrapped

A box marked with a lime green X

A box melted out of shape

A box sealed with a lipstick kiss

A box reeking of oil

10

A box showing signs of repair"""

# 清洗数据并过滤干扰行
def process_text(text):
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    
    # 需要跳过的标题关键词
    skip_keywords = {
        "1d10", "Your Mystery Box",
        "1d6", "Inside the Box is..."
    }
    
    # 分离有效内容
    filtered = []
    for line in lines:
        if line in skip_keywords:
            continue
        # 合并被错误换行的数字（如 10 被分割成 1 和 0 的情况）
        if line.isdigit() or (len(line) == 1 and line in "0123456789"):
            filtered.append(line)
        else:
            filtered.append(line)
    
    return filtered

# 智能配对数字与描述
def build_table(lines):
    numbers = []
    descriptions = []
    
    # 状态追踪器
    expecting_number = True
    
    for line in lines:
        if line.isdigit():
            if expecting_number:
                numbers.append(line)
                expecting_number = False
            else:
                # 处理连续数字的情况
                numbers[-1] += line  # 合并被分割的数字如 1 和 0 → 10
        else:
            if not expecting_number:
                descriptions.append(line)
                expecting_number = True
    
    # 验证数据完整性
    if len(numbers) != len(descriptions):
        print(f"警告: 数字数量({len(numbers)}) ≠ 描述数量({len(descriptions)})")
    
    return numbers, descriptions

# 生成Markdown表格
def generate_markdown(numbers, descriptions):
    header = "| 1d10 | Your Mystery Box            |\n"
    separator = "|------|-----------------------------|\n"
    body = ""
    
    for num, desc in zip(numbers, descriptions):
        body += f"| {num:<4} | {desc:<27} |\n"
    
    return header + separator + body

# 执行处理流程
filtered_lines = process_text(text)
numbers, descriptions = build_table(filtered_lines)
print(generate_markdown(numbers, descriptions))