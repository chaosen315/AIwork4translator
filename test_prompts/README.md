# 提示词测试工具

这个目录包含了用于测试和调优翻译提示词的工具和样例。

## 文件说明

- `test_samples.md` - 测试样例集，包含不同类型的文本
- `test_terms.csv` - 术语词典，用于测试专有名词翻译
- `test_prompts.py` - 主要测试脚本
- `test_results/` - 测试结果保存目录（自动生成）

## 使用方法

### 基本测试
```bash
# 测试默认提供商 (kimi)
python test_prompts\test_prompts.py

# 测试指定提供商
python test_prompts\test_prompts.py deepseek
```

### 支持的提供商
- kimi (默认)
- deepseek
- gpt
- sillion
- gemini
- doubao

### 测试内容

测试脚本会自动：
1. 加载测试样例和术语词典
2. 调用API进行翻译
3. 分析输出格式是否符合要求
4. 检查正文和译注的分离情况
5. 生成详细的测试报告

### 输出结果

测试结果会保存在 `test_results/` 目录下：
- `test_results_<provider>_<timestamp>.json` - 详细的JSON格式结果
- `test_results_<provider>_<timestamp>.txt` - 人类可读的文本格式

### 自定义测试

你可以：
1. 编辑 `test_samples.md` 添加更多测试样例
2. 修改 `test_terms.csv` 调整术语词典
3. 在 `test_prompts.py` 中调整分析逻辑

## 测试指标

- **格式合规性**：是否按照要求分为正文和译注两部分
- **翻译质量**：正文是否通顺准确
- **术语处理**：是否正确使用术语词典中的译名
- **新术语识别**：是否能识别并注释未在词典中的新术语

## 提示词调优建议

1. **格式问题**：如果格式不合规，可以调整 `BASE_PROMPT` 中的格式说明
2. **术语遗漏**：如果新术语未被识别，可以强化术语识别指令
3. **译注质量**：如果译注不够详细，可以添加更具体的说明要求
4. **正文流畅度**：如果正文不够通顺，可以调整翻译风格指令