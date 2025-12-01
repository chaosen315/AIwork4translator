from dotenv import load_dotenv
from time import perf_counter
import csv
load_dotenv(dotenv_path=r"data\.env")
import os
from modules.config import global_config
from modules.read_tool import read_structured_paragraphs
from modules.csv_process_tool import get_valid_path, validate_csv_file
from modules.api_tool import LLMService
from modules.write_out_tool import write_to_markdown
from modules.markitdown_tool import markitdown_tool
from modules.count_tool import count_md_words

def main():
    PS = False
    CHUNK_SIZE = global_config.max_chunk_size
    llm_service = LLMService(provider="kimi")
    input_md_file="input_files\RTG-CPR-DLC-HopeRebornPlusv1.1_md_form_for_input.md"
    input_dir = os.path.dirname(input_md_file)
    input_filename = os.path.basename(input_md_file)
    base_name, extension = os.path.splitext(input_filename)
    output_base_filename = f"{base_name}_output"
    output_md_file = os.path.join(input_dir, f"{output_base_filename}{extension}")
    csv_file = "input_files/test0411-sheet1-3.csv"
    start_time = perf_counter()
    counter = 1
    while os.path.exists(output_md_file):
        output_md_file = os.path.join(input_dir, f"{output_base_filename}_{counter}{extension}")
        counter += 1
    paragraphs = read_structured_paragraphs(input_md_file,max_chunk_size=CHUNK_SIZE,preserve_structure=False)
    total_token = 0
    for segment in paragraphs:
        if PS:
            paragraph, meta_data = segment
        else:
            paragraph = segment
            meta_data = None
        prompt = llm_service.create_prompt(paragraph, {})
        try:
            response,usage_tokens = llm_service.call_ai_model_api(prompt)
        except Exception as e:
            print(f"API调用失败：{e}")
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
        print(f"已处理一段内容，输出已保存到 {output_md_file}")
    end_time = perf_counter()
    time_taken = end_time-start_time
    print(f'Time taken: {time_taken:.2f} seconds.')
    raw_len = count_md_words(input_md_file)
    processed_len = count_md_words(output_md_file)
    new_row = [str(input_md_file),raw_len,str(output_md_file),processed_len,total_token,time_taken]
    file_exists = os.path.isfile('counting_table.csv') and os.path.getsize('counting_table.csv') > 0
    with open('counting_table.csv','a',newline='',encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        if not file_exists:
            writer.writerow(['Input file','Input len','Output file','Output len','Tokens','Taken time'])
        writer.writerow(new_row)
if __name__ == "__main__":
    main()
