# AIwork4translator

Precise AI translation method with noun comparison list.

## 程序结构

```python
project_root/
├── data/
│   ├── .env
├── src/
│   ├── main.py
│   ├── test_api_tool.py
│   └── modules/
│       ├── __init__.py
│       ├── api_tool.py
│       ├── config.py
│       ├── csv_process_tool.py
│       ├── markitdown_tool.py
│       ├── read_tool.py
│       └── write_out_tool.py
```

## 原理

这个程序的亮点是通过正则的方法捕捉文段中的专有名词，以确保llm在进行翻译时能够对专有名词进行准确的翻译。

由于名词表天然地不可能包括新的文本中的新名词，所以在ai翻译后会在文段下方附加识别到的新名词以方便校对编辑。

该程序的最严谨方法是输入md格式的原文文本文件，与csv格式的名词表文件，输出md格式的译文文本文件。

感谢Markitdown的贡献，现在它也能处理其它文件格式，不过没有经过充分测试。PDF文件的表现良好（非OCR），OCR形式的PDF文件仍有待测试。

## 特性

借助名词表的正则过滤方法，AI在翻译文本时能够更准确地使用专有名词规定的译名，同时标注出可能同样是专有名词但没有对应译名的潜在专有名词。

在此基础上，翻译者可以快速更新迭代名词表，也可以减少名词统一的重复工作量

## 支持环境

```python
Python:3.10-3.12
```

## 使用教程

接下来讲解程序的使用教程：

1. 运行`\src`文件夹中的`main.py`。
2. 选择使用的API供应商。（目前只支持kimi，gpt，deepseek）
3. 输入需要翻译的文件路径。（根据Markitdown文档的支持格式：PDF，PowerPoint，Word，Excel，HTML，基于文本的格式（CSV，JSON，XML），EPubs）
4. 输入csv格式的名词表文件路径。
5. 等待程序完成翻译并保存为md文档。

注意事项：

- 要想正常运行程序，你必须在`\data`文件夹中修改环境变量。将`API_KEY`更换为你自己的。
- 开发过程中使用的供应商是kimi，由于没有openai与deepseek的api余额，故后二者的api访问代码未经过测试。

## 名词表格式

| 原文 | 译文 |
| --- | --- |
| …… | …… |
| …… | …… |

在提供名词表后，程序设置了严格的审核步骤以确保名词表可以被正确使用。你可以提前确保以下几个标准以减少在这个步骤中需要花费的时间：

1. 确保文件无空行与空值。
2. 确保原文列无重复值。
3. 确保可以用“UTF-8”解码。

## 联系方式

chasen0315@gmail.com
