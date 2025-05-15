# AIwork4translator
Precise AI translation method with noun comparison list

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
└── test_codes/
    ├── running_test1_pos.ipynb
    ├── running_test2_pos.ipynb
    ├── running_test2.ipynb
    └── running.ipynb
```

## 原理

这个程序的亮点是通过正则的方法捕捉文段中的专有名词，以确保llm在进行翻译时能够对专有名词进行准确的翻译。

由于名词表天然地不可能包括新的文本中的新名词，所以在ai翻译后会在文段下方附加识别到的新名词以方便校对编辑。

该程序的最严谨方法是输入md格式的原文文本文件，与csv格式的名词表文件，输出md格式的译文文本文件。

感谢Markitdown的贡献，现在它也能应付其它文件格式，不过没有经过充分测试。PDF文件的表现良好（非OCR），OCR形式的PDF文件仍有待测试。

接下来讲解程序的使用教程：

1. 运行`\src`文件夹中的`main.py`。
2. 选择使用的API供应商。（目前只支持kimi，gpt，deepseek）
3. 输入需要翻译的文件路径。（根据Markitdown文档的支持格式：PDF，PowerPoint，Word，Excel，HTML，基于文本的格式（CSV，JSON，XML），EPubs）
4. 输入csv格式的名词表文件路径。
5. 等待程序完成翻译并保存为md文档。

注意事项：

- 要想正常运行程序，你必须在`\data`文件夹中修改环境变量。将`API_KEY`更换为你自己的。
- 开发过程中使用的供应商是kimi，由于没有openai与deepseek的api余额，故后二者的api访问代码未经过测试。
