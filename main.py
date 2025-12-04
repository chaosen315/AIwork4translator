from dotenv import load_dotenv
from time import perf_counter
import csv
load_dotenv(dotenv_path="data/.env")
import os, time, json
from modules.config import global_config, setup_runtime_config
from modules.read_tool import read_structured_paragraphs
from modules.csv_process_tool import get_valid_path, validate_csv_file, load_terms_dict, find_matching_terms
from modules.api_tool import LLMService
from modules.write_out_tool import write_to_markdown
from modules.markitdown_tool import markitdown_tool
from modules.count_tool import count_md_words, count_structured_paragraphs

def main():
    PS = global_config.preserve_structure
    CHUNK_SIZE = global_config.max_chunk_size
    prefs_path = os.path.join("data", ".prefs.json")
    prefs = {}
    if os.path.exists(prefs_path):
        try:
            with open(prefs_path, "r", encoding="utf-8") as f:
                prefs = json.load(f)
        except Exception:
            prefs = {}
    while True:
        default_provider = prefs.get("last_provider")
        provider_prompt = "需要确认API平台（\"kimi\",\"gpt\",\"deepseek\",\"sillion\",\"gemini\"）。"
        if default_provider:
            provider_prompt += f"上一次使用{default_provider}，如继续使用请按回车，如有更换请输入："
        else:
            provider_prompt += ": "
        provider_in = input(provider_prompt).strip()
        if not provider_in and default_provider:
            provider_in = default_provider
        llm_service = LLMService(provider=provider_in)
        print('')
        default_input = prefs.get("last_input_md_file")
        file_prompt = "需要原文文件路径。"
        if default_input:
            file_prompt += f"上一次使用{default_input}，如继续使用请按回车，如有更换请输入："
        else:
            file_prompt += ": "
        input_file = input(file_prompt).strip()
        if not input_file and default_input:
            input_file = default_input
        if not input_file:
            print("输入不能为空，请重新输入。")
            continue
        # 智能去除双引号 - 处理用户输入时可能自带的引号
        input_file = input_file.strip('"\'')  # 去除开头和结尾的双引号和单引号
        if not os.path.exists(input_file):
            print(f"错误：文件 {input_file} 不存在，请检查路径后重试。")
            continue
        _, check_extension = os.path.splitext(input_file)
        if check_extension.lower() != '.md':
            print(f"已输入的文件格式不是Markdown格式，而是{check_extension}。正在使用Markitdown插件进行格式转换……")
            input_md_file = markitdown_tool(input_file)
            if not input_md_file:
                print("请更换有效文件格式后重试。有效的文件格式例如：PDF，PowerPoint，Word，Excel，HTML，基于文本的格式（CSV，JSON，XML），EPubs")
                continue
            file_size = os.path.getsize(input_md_file)
            with open(input_md_file, 'r', encoding='utf-8') as f:
                content = f.read()
                word_count = len(content)
                paragraph_count = len([p for p in content.split('\n\n') if p.strip()])
            print(f"文件转换完成，大小为【{file_size/1024:.2f} KB】，字数为【{word_count}】，段落数量为【{paragraph_count}】")
            print(f"转换后的文件路径：")
            print(input_md_file)
            print("请打开并检查转换后的md文件内容")
            while True:
                confirm = input("是否继续翻译？如果选择n将结束程序。(y/n): ").strip().lower()
                if confirm == 'y':
                    break
                elif confirm == 'n':
                    print("程序已退出。您可以手动修改md文件后重新运行程序。")
                    return
                else:
                    print("输入无效，请输入y或n")
            PS = False
        else:
            input_md_file = input_file
        break
    input_dir = os.path.dirname(input_md_file)
    input_filename = os.path.basename(input_md_file)
    base_name, extension = os.path.splitext(input_filename)
    output_base_filename = f"{base_name}_output"
    print('')
    output_md_file = os.path.join(input_dir, f"{output_base_filename}{extension}")
    has_glossary = input("您是否已有术语表文件（csv，xlsx）？(y/n): ").strip().lower()
    if has_glossary == 'n':
        print(f'开始调取NER模型...')
        print(f'如您没有下载模型，可前往https://huggingface.co/zhayunduo/ner-bert-chinese-base下载。并将模型文件放入./models目录下。')
        from modules.ner_list_tool import EntityRecognizer
        print("正在从文档中提取专业名词生成空白名词表...")
        try:
            recognizer = EntityRecognizer()
            base_csv_path = recognizer.process_file(input_md_file)
        except Exception as e:
            print(f"名词提取失败: {str(e)}")
            print("请检查文档格式后重试")
            return
        print(f"\n空白名词表已生成: {base_csv_path}")
        print("请填写该文件中的译文列，然后重新运行程序使用名词表")
        print("程序将在5秒后退出...")
        time.sleep(5)
        return
    csv_file = get_valid_path("需要术语表文件地址（csv，xlsx）路径: ", validate_csv_file, prefs.get("last_csv_path"))
    start_time = perf_counter()
    terms_dict = load_terms_dict(csv_file)
    counter = 1
    print(f"开始翻译文档...")
    while os.path.exists(output_md_file):
        output_md_file = os.path.join(input_dir, f"{output_base_filename}_{counter}{extension}")
        counter += 1
    total_paragraphs = count_structured_paragraphs(input_md_file, max_chunk_size=CHUNK_SIZE, preserve_structure=PS)
    print(f"文档总段落数为【{total_paragraphs}】")
    print(f"开始调取文档段落...")
    paragraphs = read_structured_paragraphs(input_md_file, max_chunk_size=CHUNK_SIZE, preserve_structure=PS)
    total_token = 0
    current_paragraph = 0
    consecutive_api_failures = 0
    last_api_error = None
    for segment in paragraphs:
        current_paragraph += 1
        print(f"开始翻译段落【{current_paragraph}】/【{total_paragraphs}】")
        if PS:
            paragraph, meta_data = segment
        else:
            paragraph = segment
            meta_data = None
        specific_terms_dict = find_matching_terms(paragraph, terms_dict)
        prompt = llm_service.create_prompt(paragraph, specific_terms_dict)
        try:
            response, usage_tokens = llm_service.call_ai_model_api(prompt)
            print(response)
            #response = "\n".join([response,str(specific_terms_dict),'---'])
            response = "\n".join([response,'---'])
            consecutive_api_failures = 0
        except Exception as e:
            last_api_error = e
            consecutive_api_failures += 1
            print(f"\nAPI调用失败：{str(e)}")
            print(f"连续翻译失败次数: {consecutive_api_failures}/3")
            if consecutive_api_failures >= 3:
                print("\n连续3次翻译失败，开始进行API配置测试...")
                try:
                    test_results = llm_service.test_api()
                    print("\n=== API测试完成 ===")
                    print(f"测试结果: {test_results}")
                    print(f"最后一次API调用错误: {str(last_api_error)}")
                    print(f"\n请检查API配置或网络连接后重新运行程序。")
                    print("配置文件位置: data/.env")
                except Exception as test_e:
                    print(f"\nAPI测试过程中发生错误: {str(test_e)}")
                    print(f"最后一次API调用错误: {str(last_api_error)}")
                    print("\n请检查API配置或网络连接后重新运行程序。")
                    print("配置文件位置: data/.env")
                return
            continue
        total_token += usage_tokens
        if PS:
            write_to_markdown(
                output_md_file,
                (response, meta_data),
                mode='structured'
            )
        else:
            write_to_markdown(output_md_file,
                              (response, meta_data),
                              mode='flat')
        print(f"已处理第{current_paragraph}段内容，输出已保存到：")
        print(output_md_file)
    end_time = perf_counter()
    time_taken = end_time-start_time
    print(time.strftime('共耗时：%H时%M分%S秒', time.gmtime(int(time_taken))))
    raw_len = count_md_words(input_md_file)
    processed_len = count_md_words(output_md_file)
    new_row = [str(input_md_file),raw_len,str(output_md_file),processed_len,total_token,time_taken]
    file_exists = os.path.isfile('counting_table.csv') and os.path.getsize('counting_table.csv') > 0
    with open('counting_table.csv','a',newline='',encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        if not file_exists:
            writer.writerow(['Input file','Input len','Output file','Output len','Tokens','Taken time'])
        writer.writerow(new_row)
    new_prefs = {
        "last_provider": provider_in,
        "last_input_md_file": input_md_file,
        "last_csv_path": csv_file,
    }
    try:
        os.makedirs("data", exist_ok=True)
        with open(prefs_path, "w", encoding="utf-8") as f:
            json.dump(new_prefs, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

if __name__ == "__main__":
    main()
