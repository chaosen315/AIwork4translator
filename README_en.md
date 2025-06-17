# AIwork4translator

## Program Structure

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

## Principle

The highlight of this program is that it captures proper nouns in the text through regular expression methods to ensure that LLM can accurately translate the proper nouns when translating. Preliminary experimental tests show that this method can save 99% of the additional token consumption caused by traditional RAG technology, and the number of proper nouns captured has increased by 35% compared to traditional RAG technology. The quality of text translation has significantly improved due to the enhanced accuracy of proper nouns.

Since it is naturally impossible for a noun list to include new nouns in a new text, the identified new nouns will be added below the text after AI translation to facilitate proofreading and editing.

The most rigorous method of this program is to input the original text file in md format and the noun table file in csv format, and output the translated text file in md format.

Thanks to [markitdown](https://github.com/microsoft/markitdown), it can now handle other file formats, but it has not been fully tested. PDF files work well (non-OCR), OCR PDF files still need to be tested.

## Characteristic

1. Through the entity noun recognition task of large models, it is possible to identify and generate a blank noun list of most entity nouns in the original text, providing translators with a quick way to determine the translation norms for terms. (Currently only available in command-line implemented programs.)
2. With the help of the regular filtering method of the noun table, AI can more accurately use the specified translations of proper nouns when translating texts, while marking potential proper nouns that may also be proper nouns but do not have corresponding translations.
3. On this basis, translators can quickly update and iterate the noun table, and also reduce the repetitive work of noun unification.

P.S. For readers who use non-Chinese languages: This project can theoretically also be applied to the translation of Chinese into foreign languages, but it is necessary to manually modify the prompts in `\modules\api_tool.py`.

## Effect Display

![image1](https://github.com/chaosen315/AIwork4translator/blob/1.0.0-release/images/444430551-b22bfb0e-d7a9-40f7-8f69-b02b524b5b08.jpg)

## Supportive Environment

```python
Python:3.10-3.12
```

## Tutorial for using the command-line implementation

Here's a tutorial for executing a program using command-line instructions:

0. Download `requirements.txt` and execute `pip install -r requirements.txt`.
1. Download the `\src` and `\data` folders.
2. Modify the environment variable in `\data\.env`, copy and paste your API KEY into it, and save it.
3. Run `main.py` in the `\src` folder.
4. Choose the API vendor you want to use. (Currently only kimi, gpt, deepseek, ollama are supported)
5. Enter the path of the file to be translated. (Supported formats according to Markitdown documents: PDF, PowerPoint, Word, Excel, HTML, text-based formats (CSV, JSON, XML), EPubs)
6. If there is no noun table in csv format, enter `n` to enter the blank noun table generation process. After the blank noun table generation is completed, the program will automatically close.
(Note: In order to implement this function, you need to download the model file from the [huggingface](https://huggingface.co/chaosen/bert-large-cased-finetuned-conll03-english-for-ner) link to the `.\models\bert-large-cased-finetuned-conll03-english-for-ner` folder. For the specific structure, please refer to the program structure diagram at the beginning of the document.)
7. If you already have a noun table in csv format and have entered the corresponding translation, enter `y` to enter the noun table file upload process.
8. Enter the path of the noun table file in csv format.
8. Enter the path to the glossary file in CSV format.
9. Wait for the program to finish translating and save as an Markdown document.

Notes:

- In order to run the program properly, you must modify the environment variables in the `\data` folder. Replace 'API_KEY' with your own.
- The vendor used in the development process is Kimi, and the API access code of OpenAI and Deepseek has not been tested because there is no API balance for the latter.

## Tutorial on how to use the WebUI implementation

Here is the tutorial for using the WebUI executor:

1. Download the `\webui_project` folder.
2. Modify the environment variable in `\webui_project\data\.env`, copy and paste your API KEY into it and save it.
3. Run `app.py` in the `\webui_project folder`.
4. Open the link returned by the terminal or type `http://localhost:8001/` directly into your browser.
5. Click "选择文件" and "验证文件/验证词典" in the interface, wait for the successful prompt, and then click "开始处理文本" to wait for the download link of the result file to be generated.

![image2](https://github.com/chaosen315/AIwork4translator/blob/1.0.0-release/images/444591524-9efb2f04-2aa1-4fe7-ad3d-b206f227f3d1.png)

Screenshot of the interface

![image3](https://github.com/chaosen315/AIwork4translator/blob/1.0.0-release/images/180406E35AFC69EE34ACE24CAAB3E460.png)

Download page: Select "Save As" from the right-click menu.

Note:

*   To run the program properly, you must modify the environment variables in the `\data` folder. Replace `API_KEY` with your own.
*   The provider used in the development process is Kimi. Since there is no API balance for OpenAI and Deepseek, the API access codes of the latter two have not been tested.

## Noun table format

| Original | Translation |
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

Since the md files converted by morkitdown do not have a title structure, all non-md files that need to be translated are translated through the path of "unstructured translation mode". It does not recognize the title structure of the md document.

When using md files for translation, the program processes the text in "Structured Translation Mode" by default. If the text structure does not meet the following requirements, an error may occur:

```python
1. It assumes that there are up to 6 levels of title structure in the file by default, and intelligently splits the text into sections based on the text structure.
2. Its default line symbol is two line breaks.
```
The on-premise deployment model of Ollama is now supported. The local model is invoked by modifying the OLLAMA_BASE_URL and OLLAMA_MODEL in `\data\.env`.
## Contact Details

If you have more ideas about the program or encounter deployment problems, you can send an email to [chasen0315@gmail.com](mailto:chasen0315@gmail.com) . We will respond within 48 hours (until 20/5/2025) at the latest.
