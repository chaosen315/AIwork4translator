# app.py
import os
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request,UploadFile
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse
from pathlib import Path
from modules.config import global_config, setup_runtime_config
from modules.read_tool import read_structured_paragraphs
from modules.csv_process_tool import validate_csv_file, load_terms_dict, find_matching_terms
from modules.api_tool import LLMService
from modules.write_out_tool import write_to_markdown
from modules.markitdown_tool import markitdown_tool
from dotenv import load_dotenv
import uvicorn
import shutil
load_dotenv(dotenv_path="data\.env")
app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)
@app.get("/")
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})
PS = global_config.preserve_structure
@app.post("/validate-file")
async def validate_file(
    file: UploadFile = File(...),
    file_type: str = Form(...)  # 'md' or 'csv'
):
    try:
        # 保存上传的文件
        file_path = UPLOAD_DIR / file.filename
        print(file_path)
        with file_path.open("wb") as f:
            shutil.copyfileobj(file.file, f)
        print("shutil执行成功")
        if file_type != 'csv':
            print(f"已上传原文文件，开始验证是否md文件……")
            global PS
            PS = True
            print(f"PS值：{PS}")
            # 检查文件格式，如果需要则进行转换
            print(file_type)
            _, check_extension = os.path.splitext(str(file_path))
            if check_extension.lower() != '.md':
                print(f"检测到文件格式非md。是{check_extension}")
                try:
                    converted_path = markitdown_tool(str(file_path))
                    print(f"转换后文件路径：{converted_path}")
                    if not converted_path:
                        return JSONResponse({
                            "status": "error",
                            "message": "文件格式转换失败，请上传支持的文件格式"
                        })
                    PS=False
                    print(f"PS值：{PS}")
                    file_path = Path(converted_path)
                except Exception as e:
                    return JSONResponse({
                        "status": "error",
                        "message": f"文件转换错误：{str(e)}"
                    })

            
        elif file_type == 'csv':
            # 验证CSV文件
            if not validate_csv_file(str(file_path)):
                return JSONResponse({
                    "status": "error",
                    "message": "CSV文件格式无效，请检查文件内容"
                })
        print("文件已处理完毕，开始回传参数")
        
        return JSONResponse({
            "status": "success",
            "message": "文件验证通过",
            "file_path": str(file_path)
        })

    except Exception as e:
        print("函数执行出错")
        return JSONResponse({
            "status": "error",
            "message": f"文件处理错误：{str(e)}"
        })

def process_files(input_md_file: str, csv_file: str, llm_provider: str) -> str:
    # 初始化服务
    print("开始处理文本。")
    try:
        llm_service = LLMService()
    except Exception as e:
        print(e)
    llm_service.provider = llm_provider
    print("已连接API")
    # 调取临时配置（推荐常用方式）
    print("开始调取配置。")
    preservestructure = PS
    print(PS)
    print(preservestructure)
    CHUNK_SIZE = global_config.max_chunk_size
    print(CHUNK_SIZE)

    # 生成输出文件路径（与输入文件同一目录，文件名添加"_output"后缀）
    input_dir = os.path.dirname(input_md_file)
    input_filename = os.path.basename(input_md_file)
    base_name, extension = os.path.splitext(input_filename)
    output_base_filename = f"{base_name}_output"
    output_md_file = os.path.join(input_dir, f"{output_base_filename}{extension}")
    print(output_md_file)
    # 初始化
    terms_dict = load_terms_dict(csv_file)
    # 如果输出文件已存在，添加编号后缀
    counter = 1
    while os.path.exists(output_md_file):
        output_md_file = os.path.join(input_dir, f"{output_base_filename}_{counter}{extension}")
        counter += 1
        # 逐段处理（可打断）
    # print(PS)
    print("开始逐段处理")
    paragraphs = read_structured_paragraphs(input_md_file,max_chunk_size=CHUNK_SIZE,preserve_structure=PS)
    # 处理循环改造
    for segment in paragraphs:
        # 结构化模式解包
        if preservestructure:
            paragraph, meta_data = segment
            print("Structure")
        else:
            paragraph = segment
            meta_data = None
            print("flat")
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
        if preservestructure:
            write_to_markdown(
                output_md_file,
                (response, meta_data),  # 携带元数据
                mode='structured'
            )
        else:
            write_to_markdown(output_md_file,
                                (response, meta_data),  # 携带元数据
                                mode='flat')
    
    return output_md_file

@app.post("/process")
async def process_endpoint(
    md_path: str = Form(...),
    csv_path: str = Form(...),
    llm_provider: str = Form(...)
):
    try:
        # 调用主函数处理逻辑
        print(md_path,type(md_path))
        print(csv_path,type(csv_path))
        print(llm_provider)
        result = process_files(md_path, csv_path, llm_provider)
        return JSONResponse({
            "status": "success",
            "message": "处理完成",
            "output_file": result
        })
    except Exception as e:
        print(f"主函数调用失败：{e}")
        raise HTTPException(status_code=500, detail=str(e))

# @app.get("/progress")
# async def get_progress():
#     current_progress = 0

#     def update_progress(progress: int):
#         global current_progress
#         current_progress = progress

#     return {"progress": current_progress}

if __name__ == "__main__":
    uvicorn.run(app, host="localhost", port=8001)