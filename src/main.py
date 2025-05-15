from dotenv import load_dotenv
# 加载环境变量
load_dotenv(dotenv_path="data\.env")
import os
from modules.config import global_config, setup_runtime_config
from modules.read_tool import read_structured_paragraphs
from modules.csv_process_tool import get_valid_path, validate_csv_file, load_terms_dict, find_matching_terms
from modules.api_tool import LLMService
from modules.write_out_tool import write_to_markdown
from modules.markitdown_tool import markitdown_tool

# 加载环境变量
load_dotenv(dotenv_path="data\.env")


# 主程序流程
def main():
    # 方式一：直接使用全局配置（推荐常用方式）
    PS = global_config.preserve_structure
    CHUNK_SIZE = global_config.max_chunk_size
    
    # 方式二：临时获取用户交互配置（会返回新配置实例，不影响全局）
    # runtime_config = setup_runtime_config()
    # PS = runtime_config.preserve_structure
    # CHUNK_SIZE = runtime_config.max_chunk_size

    # 通过input()获取输入文件路径
    # 动态获取输入文件路径，直到提供有效路径
    while True:
        # 初始化服务（默认使用Kimi）
        llm_service = LLMService(provider=input("""请选择需要使用的API平台（"kimi","gpt","deepseek"）:""".strip()))

        input_file = input("请输入文件路径: ").strip()

        # 检查输入是否为空
        if not input_file:
            print("输入不能为空，请重新输入。")
            continue

        # 检查文件是否存在
        if not os.path.exists(input_file):
            print(f"错误：文件 {input_file} 不存在，请检查路径后重试。")
            continue  # 文件不存在，重新循环
            
        _, check_extension = os.path.splitext(input_file)
        if check_extension .lower() != '.md':
            print(f"已输入的文件格式不是Markdown格式，而是{check_extension}。正在使用Markitdown插件进行格式转换……")
            
            input_md_file = markitdown_tool(input_file)
            if not input_md_file:
                print("请更换有效文件格式后重试。有效的文件格式例如：PDF，PowerPoint，Word，Excel，HTML，基于文本的格式（CSV，JSON，XML），EPubs")
                continue #文件解析失败，重新开始循环
            print("已成功转换格式为md文件。已保存在原文件夹。")  
            PS = False     
        else:
            input_md_file = input_file
        break

    # 生成输出文件路径（与输入文件同一目录，文件名添加"_output"后缀）
    input_dir = os.path.dirname(input_md_file)
    input_filename = os.path.basename(input_md_file)
    base_name, extension = os.path.splitext(input_filename)
    output_base_filename = f"{base_name}_output"
    output_md_file = os.path.join(input_dir, f"{output_base_filename}{extension}")

    # 获取并验证CSV文件路径
    csv_file = get_valid_path("请输入名词表CSV文件路径: ", validate_csv_file)

    # 初始化
    terms_dict = load_terms_dict(csv_file)

    # 如果输出文件已存在，添加编号后缀
    counter = 1
    while os.path.exists(output_md_file):
        output_md_file = os.path.join(input_dir, f"{output_base_filename}_{counter}{extension}")
        counter += 1

    # 逐段处理（可打断）
    # print(PS)
    paragraphs = read_structured_paragraphs(input_md_file,max_chunk_size=CHUNK_SIZE,preserve_structure=PS)
    # 处理循环改造
    for segment in paragraphs:
        # 结构化模式解包
        if PS:
            paragraph, meta_data = segment
        else:
            paragraph = segment
            meta_data = None
        # 检测专业名词
        specific_terms_dict = find_matching_terms(paragraph, terms_dict)

        # 构造prompts并调用API
        prompt = llm_service.create_prompt(paragraph, specific_terms_dict)
        try:
            response = llm_service.call_ai_model_api(prompt)
        except Exception as e:
            print(f"API调用失败：{e}")
            continue

        # 写入输出文件
        if PS:
            write_to_markdown(
                output_md_file,
                (response, meta_data),  # 携带元数据
                mode='structured'
            )
        else:
            write_to_markdown(output_md_file,
                                (response, meta_data),  # 携带元数据
                                mode='flat')

        # 提示用户可以查看输出文件
        print(f"已处理一段内容，输出已保存到 {output_md_file}")

        # 在这里可以添加用户交互逻辑，比如询问是否继续处理下一段

if __name__ == "__main__":
    main()