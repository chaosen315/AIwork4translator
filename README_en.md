# AIwork4translator

## Program Structure

```python
project_root/
├── data/
│   ├── .env
├── src/
│   ├── main.py
│   └── modules/
│       ├── __init__.py
│       ├── api_tool.py
│       ├── config.py
│       ├── csv_process_tool.py
│       ├── markitdown_tool.py
│       ├── read_tool.py
│       └── write_out_tool.py
```

## Principle

The highlight of this program is that it captures proper nouns in the text through regular expression methods to ensure that LLM can accurately translate the proper nouns when translating.

Since it is naturally impossible for a noun list to include new nouns in a new text, the identified new nouns will be added below the text after AI translation to facilitate proofreading and editing.

The most rigorous method of this program is to input the original text file in md format and the noun table file in csv format, and output the translated text file in md format.

Thanks to Markitdown, it can now handle other file formats, but it has not been fully tested. PDF files work well (non-OCR), OCR PDF files still need to be tested.

## Characteristic

With the help of the regular filtering method of the noun table, AI can more accurately use the specified translations of proper nouns when translating texts, while marking potential proper nouns that may also be proper nouns but do not have corresponding translations.

On this basis, translators can quickly update and iterate the noun table, and also reduce the repetitive work of noun unification.

P.S. For readers who use non-Chinese languages: This project can theoretically also be applied to the translation of Chinese into foreign languages, but it is necessary to manually modify the prompts in `\modules\api_tool.py`.

## Supportive Environment

```python
Python:3.10-3.12
```

## Tutorial

Next, we will explain the usage tutorial of the program:

1.  Run `main.py` in the `\src` folder.
2.  Select the API provider to use. (Currently only kimi, gpt, deepseek are supported)
3.  Enter the path to the file that needs to be translated. (Supported formats for Markitdown documents: PDF, PowerPoint, Word, Excel, HTML, text-based formats (CSV, JSON, XML), EPubs)
4.  Enter the path to the noun table file in csv format.
5.  Wait for the program to complete the translation and save it as an md document.

Note:

*   To run the program properly, you must modify the environment variables in the `\data` folder. Replace `API_KEY` with your own.
*   The provider used in the development process is Kimi. Since there is no API balance for OpenAI and Deepseek, the API access codes of the latter two have not been tested.

## Noun table format

| original | Translation |
| --- | --- |
| …… | …… |
| …… | …… |

After providing the glossary, the program sets up a strict review step to ensure that the glossary can be used correctly. You can ensure the following standards in advance to reduce the time spent on this step:

```python
1. Make sure the file has no blank lines or empty values.
2. Ensure that there are no duplicate values ​​in the source column.
3. Make sure it can be decoded with "UTF-8".
```

## Advanced Use

Since the md files converted by Workitdown do not have a title structure, all non-md files that need to be translated are translated through the path of "unstructured translation mode". It does not recognize the title structure of the md document.

When using md files for translation, the program processes the text in "Structured Translation Mode" by default. If the text structure does not meet the following requirements, an error may occur:

```python
1. 它默认文件中存在最多6级的标题结构，并智能地根据文本结构来进行文段切割。
2. 它默认的分行符号为两个换行符号。
```

## Contact Details

If you have more ideas about the program or encounter deployment problems, you can send an email to [chasen0315@gmail.com](mailto:chasen0315@gmail.com) . We will respond within 48 hours (until 20/5/2025) at the latest.
