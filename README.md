# AIwork4translator

Precise AI translation method with noun comparison list.

中文 | [English](./README_en.md)

## 程序结构

```python
project_root/
├── data/
│   └── .env
├── models/
│   └── bert-large-cased-finetuned-conll03-english-for-ner/
│       ├── config.json
│       ├── gitattributes
│       ├── model.safetensors
│       ├── special_tokens_map.json
│       ├── tokenizer.json
│       ├── tokenizer_config.json
│       └── vocab.txt
├── src/
│   ├── main.py
│   └── modules/
│       ├── __init__.py
│       ├── api_tool.py
│       ├── config.py
│       ├── count_tool.py
│       ├── csv_process_tool.py
│       ├── markitdown_tool.py
│       ├── ner_list_tool.py
│       ├── read_tool.py
│       └── write_out_tool.py
├── webui_project/
│   ├── data/
│       └── .env
│   ├── app.py
│   ├── modules/
│       ├── __init__.py
│       ├── api_tool.py
│       ├── config.py
│       ├── count_tool.py
│       ├── csv_process_tool.py
│       ├── markitdown_tool.py
│       ├── read_tool.py
│       └── write_out_tool.py
│   ├── static/
│       ├── script.js
│       └── style.css
│   ├── templates/
│       └── index.html
│   ├── uploads/
│       └── readme.md

```

## 原理

这个程序的亮点是通过正则的方法捕捉文段中的专有名词，以确保llm在进行翻译时能够对专有名词进行准确的翻译。初步实验测试，该方法可以节省99%传统rag技术导致的额外token消耗，专有名词的捕获数量相比传统rag技术增加35%。文本翻译的质量因名词准确度的改善有显著提升。

由于名词表天然地不可能包括新的文本中的新名词，所以在ai翻译后会在文段下方附加识别到的新名词以方便校对编辑。

该程序的最严谨方法是输入md格式的原文文本文件，与csv格式的名词表文件，此后程序会输出md格式的译文文本文件。

感谢[markitdown](https://github.com/microsoft/markitdown)的贡献，现在它也能处理其它文件格式，不过没有经过充分测试。PDF文件的表现良好（非OCR），OCR形式的PDF文件仍有待测试。

## 特性

1. 通过大模型的实体名词识别任务，可以实现将全新的原文文本中的绝大多数实体名词识别并生成空白的名词表，供翻译者快速厘定术语的翻译规范。（目前仅在命令行实现的程序中可用。）

2. 借助名词表的正则过滤方法，AI在翻译文本时能够更准确地使用专有名词规定的译名，同时标注出可能同样是专有名词但没有对应译名的潜在专有名词。

3. 在此基础上，翻译者可以快速更新迭代名词表，也可以减少名词统一的重复工作量。

## 效果演示

![image1](https://github.com/chaosen315/AIwork4translator/blob/1.0.0-release/images/444430551-b22bfb0e-d7a9-40f7-8f69-b02b524b5b08.jpg)

## 支持环境

```python
Python:3.10-3.13
```

## 命令行实现的使用教程

这是使用命令行指令执行程序的使用教程：

0. 下载`requirements.txt`并执行`pip install -r requirements.txt`
1. 下载`\src`与`\data`文件夹。
2. 修改`\data\.env`中的环境变量，将自己的API KEY复制粘贴进去并保存。
3. 运行`\src`文件夹中的`main.py`。
4. 选择使用的API供应商。（目前只支持kimi，gpt，deepseek,ollama）
5. 输入需要翻译的文件路径。（根据Markitdown文档的支持格式：PDF，PowerPoint，Word，Excel，HTML，基于文本的格式（CSV，JSON，XML），EPubs）
6. 如果没有csv格式的名词表，输入n进入空白名词表生成流程，空白名词表生成结束后程序将自动关闭。
（注意：为了实现该功能，你需要通过[huggingface](https://huggingface.co/chaosen/bert-large-cased-finetuned-conll03-english-for-ner)链接下载模型文件到`.\models\bert-large-cased-finetuned-conll03-english-for-ner`文件夹中,具体结构详见文档开头的程序结构示意图。)
7. 如果已有csv格式的名词表且已经输入对应的译文，输入y进入名词表文件上传流程。
8. 输入csv格式的名词表文件路径。
9. 等待程序完成翻译并保存为md文档。

注意事项：

- 要想正常运行程序，你必须在`\data`文件夹中修改环境变量。将`API_KEY`更换为你自己的。
- 开发过程中使用的供应商是kimi，由于没有openai与deepseek的api余额，故后二者的api访问代码未经过测试。

## webui实现的使用教程

这是使用webui执行程序的使用教程：

1.下载`\webui_project`文件夹。
2. 修改`\webui_project\data\.env`中的环境变量，将自己的API KEY复制粘贴进去并保存。
3. 运行`\webui_project`文件夹中的`app.py`。
4. 打开终端返回的链接，或者直接在浏览器中输入`http://localhost:8001/`。
5. 在界面中依次点击“选择文件”与“验证文件/词典”，等待成功提示后，选择所使用的API供应平台与模型。
6. 点击“开始处理文本”即可等待结果文件的下载链接生成。

![image2](https://github.com/chaosen315/AIwork4translator/blob/1.0.0-release/images/444591524-9efb2f04-2aa1-4fe7-ad3d-b206f227f3d1.png)

界面截图

![image3](https://github.com/chaosen315/AIwork4translator/blob/1.0.0-release/images/180406E35AFC69EE34ACE24CAAB3E460.png)

下载页面：在右键菜单中选择“另存为”即可。

## 名词表格式

| 原文 | 译文 |
| --- | --- |
| …… | …… |
| …… | …… |

在提供名词表后，程序设置了严格的审核步骤以确保名词表可以被正确使用。你可以提前确保以下几个标准以减少在这个步骤中需要花费的时间：

```python
1. 确保文件无空行与空值。
2. 确保原文列无重复值。
3. 确保可以用“UTF-8”解码。
```

## 进阶使用

由于morkitdown转化的md文件不存在标题结构，所以需要翻译的非md文件都是通过“非结构化翻译模式”的路径进行翻译的。它不会识别md文档的标题结构。

使用md文件进行翻译，则程序默认通过“结构化翻译模式”进行文本处理。如果文本结构不符合下述要求，则有概率出现报错：

```python
1. 它默认文件中存在最多6级的标题结构，并智能地根据文本结构来进行文段切割。
2. 它默认的分行符号为两个换行符号。
```
现已支持ollama本地部署模型的接入。通过修改`\data\.env`中的`OLLAMA_BASE_URL`与`OLLAMA_MODEL`来调用本地模型。
## 联系方式

对于该程序有更多想法或遇到部署问题可以发信至chasen0315@gmail.com。最迟24小时内（截止20/5/2025）会进行回复。
