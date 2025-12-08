from dotenv import load_dotenv
from time import perf_counter
import csv
load_dotenv(dotenv_path="data/.env")
import os, time, json
from modules.config import global_config, setup_runtime_config
from modules.read_tool import read_structured_paragraphs
from modules.csv_process_tool import get_valid_path, validate_csv_file, load_terms_dict, find_matching_terms
from modules.terminology_tool import load_glossary_df, merge_new_terms, save_glossary_df, dict_to_df, save_terms_result
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
    # 构建一个空白的CSV文件路径，作为函数save_terms_result的参数
    blank_csv_path = os.path.join(input_dir, f"{base_name}_output_terminology.csv")
    print('')
    output_md_file = os.path.join(input_dir, f"{output_base_filename}{extension}")
    while True:
        has_glossary = input("您是否已有术语表文件（csv，xlsx）？(y/n): ").strip().lower()
        if has_glossary == 'n':
            # 以base_name为名，后缀为_terminology，构建一个空白的csv文件，表头为“term,译名”
            with open(blank_csv_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(["原文", "译名"])
                writer.writerow(["England", "英格兰"])
            print(f"程序将在翻译结束后生成术语表文件。")
            csv_file = blank_csv_path
            break
            # 通过实体识别模型提取专业名词生成空白名词表，现阶段为废弃状态
            # print(f'开始调取NER模型...')
            # print(f'如您没有下载模型，可前往https://huggingface.co/zhayunduo/ner-bert-chinese-base下载。并将模型文件放入./models目录下。')
            # from modules.ner_list_tool import EntityRecognizer
            # print("正在从文档中提取专业名词生成空白名词表...")
            # try:
            #     recognizer = EntityRecognizer()
            #     base_csv_path = recognizer.process_file(input_md_file)
            # except Exception as e:
            #     print(f"名词提取失败: {str(e)}")
            #     print("请检查文档格式后重试")
            #     return
            # print(f"\n空白名词表已生成: {base_csv_path}")
            # print("请填写该文件中的译文列，然后重新运行程序使用名词表")
            # print("程序将在5秒后退出...")
            # time.sleep(5)
            # return
        elif has_glossary == 'y':
            csv_file = get_valid_path("需要术语表文件地址（csv，xlsx）路径: ", validate_csv_file, prefs.get("last_csv_path"))
            break
        else:
            print("输入无效，请输入y或n")
    start_time = perf_counter()
    terms_dict = load_terms_dict(csv_file)
    glossary_df = load_glossary_df(csv_file)
    aggregated_new_terms = []
    if has_glossary == 'y':
        merge_choice = input("是否将新术语合并到术语表？(y/n): ").strip().lower()
    if has_glossary == 'n':
        merge_choice = 'y'
    merge_in_place = (merge_choice == 'y')
    if not merge_in_place:
        blank_csv_path = os.path.join(input_dir, f"{base_name}_output_terminology.csv")
        print(f"新术语会作为新的术语表保存到与输入文件相同的目录下。")
    new_terms_df = None
    counter = 1
    print(f"开始翻译文档...")
    while os.path.exists(output_md_file):
        output_md_file = os.path.join(input_dir, f"{output_base_filename}_{counter}{extension}")
        counter += 1
    total_paragraphs = count_structured_paragraphs(input_md_file, max_chunk_size=CHUNK_SIZE, preserve_structure=PS)
    print(f"文档总段落数为【{total_paragraphs}】")
    print(f"开始调取文档段落...")
    paragraphs = read_structured_paragraphs(input_md_file, max_chunk_size=CHUNK_SIZE, preserve_structure=PS)
    
    # 监控模块初始化
    dashboard_timestamp = time.strftime("%Y%m%d_%H%M%S")
    dashboard_csv_path = f"{base_name}_{dashboard_timestamp}_dashboard.csv"
    with open(dashboard_csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([
            'Paragraph_ID', 
            'Term_Matching_Time_s', 
            'Total_API_Time_s', 
            'Pure_API_Time_s', 
            'JSON_Repair_Time_s', 
            'Retry_Count', 
            'Token_Usage', 
            'Timestamp'
        ])
        
    total_token = 0
    current_paragraph = 0
    consecutive_api_failures = 0
    last_api_error = None
    last_paragraph_text = None
    try:
        for segment in paragraphs:
            current_paragraph += 1
            print(f"开始翻译段落【{current_paragraph}】/【{total_paragraphs}】")
            if PS:
                paragraph, meta_data = segment
            else:
                paragraph = segment
                meta_data = None
            last_paragraph_text = paragraph
            union_terms_dict = terms_dict.copy()
            if aggregated_new_terms:
                for nt in aggregated_new_terms:
                    k = str(nt.get('term', '')).strip()
                    v = str(nt.get('translation', '')).strip()
                    if k and k not in union_terms_dict:
                        union_terms_dict[k] = v
            
            tm_start = perf_counter()
            specific_terms_dict = find_matching_terms(paragraph, union_terms_dict)
            tm_end = perf_counter()
            term_match_time = tm_end - tm_start

            prompt = llm_service.create_prompt(paragraph, specific_terms_dict)
            # 监控API请求耗时
            api_start = perf_counter()
            pure_api_time = 0.0
            repair_time = 0.0
            retry_count = 0

            while True:
                try:
                    p_start = perf_counter()
                    response_obj, usage_tokens = llm_service.call_ai_model_api(prompt)
                    p_end = perf_counter()
                    pure_api_time += (p_end - p_start)

                    max_retry = 5               # 最多修 5 次
                    retry = 0
                    while retry < max_retry:
                        if response_obj.get('error') != 'Invalid JSON format':
                            break               # 已经 OK，直接跳出

                        print("json格式出错，尝试修复……")
                        r_start = perf_counter()
                        repair_obj = llm_service.repair_json(response_obj.get('origin_text', ''))
                        r_end = perf_counter()
                        repair_time += (r_end - r_start)
                        retry_count += 1
                        
                        print(f"修复后的JSON响应: {repair_obj}")

                        # 把修复结果作为下一轮待检查对象
                        response_obj = repair_obj
                        retry += 1
                    # 循环结束后如果仍无效，可按业务需要处理
                    if response_obj.get('error') == 'Invalid JSON format':
                        print("修复3次失败，将重新翻译该段落。")
                        raise Exception("JSON格式修复失败")
                    break
                except Exception as e:
                    retry_count += 1
                    last_api_error = e
                    consecutive_api_failures += 1
                    print(f"\nAPI调用失败：{str(e)}")
                    print(f"连续翻译失败次数: {consecutive_api_failures}/{os.getenv('MAX_RETRIES', 3)}")
                    if consecutive_api_failures >= int(os.getenv('MAX_RETRIES', 3)):
                        print(f"\n连续{int(os.getenv('MAX_RETRIES', 3))}次翻译失败，开始进行API配置测试...")
                        try:
                            test_results = llm_service.test_api()
                            print("\n=== API测试完成 ===")
                            print(f"测试结果: {test_results}")
                            print(f"最后一次API调用错误: {str(last_api_error)}")
                            print(f"\n请检查API配置或网络连接后重新运行程序。")
                            print("配置文件位置: data/.env")
                            if isinstance(test_results, dict) and test_results.get("success"):
                                print("API测试未发现错误，可能为限流或提示词/段落设置问题。")
                                choice = input("API测试完成。是否重新开始翻译当前段落？(y/n): ").strip().lower()
                                if choice == 'y':
                                    consecutive_api_failures = 0
                                    print("正在重试当前段落...")
                                    continue
                                elif choice == 'n':
                                    break
                                else:
                                    print("输入无效，请输入y或n")
                        except Exception as test_e:
                            print(f"\nAPI测试过程中发生错误: {str(test_e)}")
                            print(f"最后一次API调用错误: {str(last_api_error)}")
                            print("\n请检查API配置或网络连接后重新运行程序。")
                            print("配置文件位置: data/.env")
                        print("任务已中断，开始保存累积的术语表……")
                        new_glossary_path = save_terms_result(merge_in_place, glossary_df, aggregated_new_terms, csv_file, blank_csv_path)
                        print("新的术语表已保存：")
                        print(new_glossary_path)
                        keyword = paragraph[:20]
                        with open(input_md_file, 'r', encoding='utf-8') as f:
                            original_content = f.read()
                        idx = original_content.find(keyword)
                        if idx != -1:
                            print("开始保存未翻译部分……")
                            untranslated_part = original_content[idx:]
                            untranslated_path = os.path.join(input_dir, f"{base_name}_rest.md")
                            with open(untranslated_path, 'w', encoding='utf-8') as uf:
                                uf.write(untranslated_part)
                            print(f"未翻译部分已保存至：{untranslated_path}")
                        else:
                            print("未找到匹配的段落，未保存未翻译部分。")
                        return
                    print("正在重试当前段落...")

            api_end = perf_counter()
            total_api_time = api_end - api_start
            
            # 写入监控数据
            # with open(dashboard_csv_path, 'a', newline='', encoding='utf-8') as f:
            #     writer = csv.writer(f)
            #     writer.writerow([
            #         current_paragraph, 
            #         f"{term_match_time:.4f}", 
            #         f"{total_api_time:.4f}", 
            #         f"{pure_api_time:.4f}", 
            #         f"{repair_time:.4f}", 
            #         retry_count, 
            #         usage_tokens, 
            #         time.strftime("%H:%M:%S")
            #     ])

            translation = response_obj.get('translation', '')
            notes = response_obj.get('notes', '')
            new_terms = response_obj.get('newterminology', [])
            aggregated_new_terms.extend(new_terms)
            if notes == '':
                response = translation
            else:
                response = "\n\n---\n\n".join([translation, notes,''])
            print(response)
            consecutive_api_failures = 0
            total_token += usage_tokens
            if PS:
                write_to_markdown(
                    output_md_file,
                    (response, meta_data),
                    mode='structured'
                )
            else:
                write_to_markdown(
                    output_md_file,
                    (response, meta_data),
                    mode='flat'
                )
            print(f"已处理第{current_paragraph}段内容，输出已保存到：")
            print(output_md_file)
    except KeyboardInterrupt:
        print("任务已中断，开始保存累积的术语表……")
        new_glossary_path = save_terms_result(merge_in_place, glossary_df, aggregated_new_terms, csv_file, blank_csv_path)
        print("新的术语表已保存：")
        print(new_glossary_path)
        if last_paragraph_text:
            keyword = last_paragraph_text[:20]
            with open(input_md_file, 'r', encoding='utf-8') as f:
                original_content = f.read()
            idx = original_content.find(keyword)
            if idx != -1:
                untranslated_part = original_content[idx:]
                untranslated_path = os.path.join(input_dir, f"{base_name}_rest.md")
                with open(untranslated_path, 'w', encoding='utf-8') as uf:
                    uf.write(untranslated_part)
                print(f"未翻译部分已保存至：{untranslated_path}")
        return
    end_time = perf_counter()
    time_taken = end_time-start_time
    print(time.strftime('共耗时：%H时%M分%S秒', time.gmtime(int(time_taken))))
    raw_len = count_md_words(input_md_file)
    processed_len = count_md_words(output_md_file)
    new_glossary_path = save_terms_result(merge_in_place, glossary_df, aggregated_new_terms, csv_file, blank_csv_path)
    print("新的术语表已保存：")
    print(new_glossary_path)
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
