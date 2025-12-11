import os
import sys
import logging
from datetime import datetime
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request, UploadFile
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse
from pathlib import Path
from modules.config import global_config, setup_runtime_config
from modules.read_tool import read_structured_paragraphs
from modules.count_tool import count_structured_paragraphs
from modules.csv_process_tool import validate_csv_file, load_terms_dict, find_matching_terms
from modules.api_tool import LLMService
from modules.write_out_tool import write_to_markdown
from modules.markitdown_tool import markitdown_tool
from dotenv import load_dotenv
import uvicorn
import shutil

def get_resource_path(relative_path):
    """获取资源文件的绝对路径（支持 PyInstaller 打包后的环境）"""
    try:
        # PyInstaller 创建临时文件夹，路径存储在 _MEIPASS 中
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

def log_action(action, details=None):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    if details:
        print(f"[{timestamp}] [ACTION] {action}: {details}")
        logger.info(f"{action}: {details}")
    else:
        print(f"[{timestamp}] [ACTION] {action}")
        logger.info(action)

def log_error(error, details=None):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    if details:
        print(f"[{timestamp}] [ERROR] {error}: {details}")
        logger.error(f"{error}: {details}")
    else:
        print(f"[{timestamp}] [ERROR] {error}")
        logger.error(error)

# 优先加载当前目录的 .env，然后尝试 data/.env
if os.path.exists(".env"):
    load_dotenv(dotenv_path=".env")
    log_action("应用启动", "从 .env 加载环境变量")
elif os.path.exists("data/.env"):
    load_dotenv(dotenv_path="data/.env")
    log_action("应用启动", "从 data/.env 加载环境变量")
else:
    log_action("应用启动", "未找到 .env 文件，使用默认配置")

app = FastAPI()
log_action("FastAPI应用创建成功")

app.mount("/static", StaticFiles(directory=get_resource_path("static")), name="static")
log_action("静态文件目录挂载", "/static -> static/")

templates = Jinja2Templates(directory=get_resource_path("templates"))
log_action("模板引擎初始化", "templates目录")

app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
log_action("上传文件目录挂载", "/uploads -> uploads/")

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)
log_action("上传目录确认", f"目录: {UPLOAD_DIR.absolute()}")
@app.get("/")
async def root(request: Request):
    log_action("访问根路径", f"客户端: {request.client.host}:{request.client.port}")
    return templates.TemplateResponse(request, "index.html")
log_action("全局配置加载", "读取全局配置项")
PS = global_config.preserve_structure
log_action("初始PS值设置", f"PS = {PS}")
@app.post("/validate-file")
async def validate_file(
    file: UploadFile = File(...),
    file_type: str = Form(...)
):
    try:
        log_action("文件验证请求", f"文件: {file.filename}, 类型: {file_type}")
        file_path = UPLOAD_DIR / file.filename
        log_action("文件保存路径", str(file_path))
        with file_path.open("wb") as f:
            shutil.copyfileobj(file.file, f)
        log_action("文件保存成功", f"大小: {file_path.stat().st_size} 字节")
        if file_type != 'csv':
            log_action("处理非CSV文件", "开始验证文件格式")
            global PS
            PS = True
            log_action("PS值更新", f"PS = {PS}")
            _, check_extension = os.path.splitext(str(file_path))
            log_action("文件扩展名检测", f"扩展名: {check_extension}")
            if check_extension.lower() != '.md':
                log_action("非MD文件检测", f"检测到格式: {check_extension}，需要转换")
                try:
                    log_action("文件转换开始", "调用markitdown_tool")
                    converted_path = markitdown_tool(str(file_path))
                    log_action("文件转换完成", f"转换后路径：{converted_path}")
                    if not converted_path:
                        log_error("文件转换失败", "转换路径为空")
                        return JSONResponse({
                            "status": "error",
                            "message": "文件格式转换失败，请上传支持的文件格式"
                        })
                    PS = False
                    log_action("PS值更新", f"PS = {PS}")
                    file_path = Path(converted_path)
                    log_action("文件路径更新", str(file_path))
                except Exception as e:
                    log_error("文件转换异常", str(e))
                    return JSONResponse({
                        "status": "error",
                        "message": f"文件转换错误：{str(e)}"
                    })
        elif file_type == 'csv':
            log_action("处理CSV文件", "开始验证CSV格式")
            is_valid, updated_path = validate_csv_file(str(file_path))
            if not is_valid:
                log_error("CSV文件验证失败", "格式无效")
                return JSONResponse({
                    "status": "error",
                    "message": "CSV文件格式无效，请检查文件内容"
                })
            # Update file_path if it was converted from XLSX
            if updated_path != str(file_path):
                file_path = Path(updated_path)
                log_action("文件路径更新", f"XLSX已转换为CSV: {file_path}")
            log_action("CSV文件验证通过", str(file_path))
        log_action("文件验证完成", "准备返回结果")
        absolute_file_path = str(file_path.absolute())
        log_action("返回文件路径", f"绝对路径: {absolute_file_path}")
        return JSONResponse({
            "status": "success",
            "message": "文件验证通过",
            "file_path": absolute_file_path,
            "preserve_structure": PS
        })
    except Exception as e:
        log_error("文件验证异常", str(e))
        return JSONResponse({
            "status": "error",
            "message": f"文件处理错误：{str(e)}"
        })

def process_files(input_md_file: str, csv_file: str, llm_provider: str) -> dict:
    log_action("处理文件开始", f"MD文件: {input_md_file}, CSV文件: {csv_file}, LLM提供商: {llm_provider}")
    try:
        log_action("LLM服务初始化", f"提供商: {llm_provider}")
        llm_service = LLMService()
        log_action("LLM服务初始化成功")
    except Exception as e:
        log_error("LLM服务初始化失败", str(e))
        return {
            "status": "error",
            "message": f"服务初始化失败",
            "error": str(e),
            "test_results": None
        }
    llm_service.provider = llm_provider
    log_action("LLM提供商设置", f"提供商: {llm_provider}")
    preservestructure = PS
    log_action("配置参数", f"preservestructure = {preservestructure}, PS = {PS}")
    CHUNK_SIZE = global_config.max_chunk_size
    log_action("配置参数", f"CHUNK_SIZE = {CHUNK_SIZE}")
    input_dir = os.path.dirname(input_md_file)
    input_filename = os.path.basename(input_md_file)
    base_name, extension = os.path.splitext(input_filename)
    output_base_filename = f"{base_name}_output"
    output_md_file = os.path.join(input_dir, f"{output_base_filename}{extension}")
    log_action("输出文件路径生成", f"路径: {output_md_file}")
    log_action("术语字典加载", f"CSV文件: {csv_file}")
    terms_dict = load_terms_dict(csv_file)
    log_action("术语字典加载完成", f"术语数量: {len(terms_dict) if terms_dict else 0}")
    counter = 1
    while os.path.exists(output_md_file):
        log_action("输出文件已存在", f"文件: {output_md_file}，添加编号后缀")
        output_md_file = os.path.join(input_dir, f"{output_base_filename}_{counter}{extension}")
        counter += 1
    log_action("最终输出文件路径", f"路径: {output_md_file}")
    consecutive_failures = 0
    MAX_CONSECUTIVE_FAILURES = 3
    last_error = None
    log_action("段落读取开始", f"文件: {input_md_file}, 分块大小: {CHUNK_SIZE}, 保留结构: {PS}")
    total_paragraphs = count_structured_paragraphs(input_md_file, max_chunk_size=CHUNK_SIZE, preserve_structure=PS)
    paragraphs = read_structured_paragraphs(input_md_file, max_chunk_size=CHUNK_SIZE, preserve_structure=PS)
    log_action("段落读取完成", f"段落数量: {total_paragraphs}")
    task_id = os.path.basename(output_md_file)
    if task_id in translation_tasks:
        translation_tasks[task_id]["total_paragraphs"] = total_paragraphs
    log_action("段落处理开始", f"总段落数: {total_paragraphs}")
    for idx, segment in enumerate(paragraphs):
        log_action(f"处理段落[{idx+1}/{total_paragraphs}]", "开始解析segment格式")
        try:
            if isinstance(segment, tuple):
                paragraph = segment[0]
                meta_data = segment[1] if len(segment) > 1 else None
                log_action(f"段落[{idx+1}]处理模式", "结构化模式 (Structure)")
                log_action(f"段落[{idx+1}]元数据", str(meta_data)[:100] + ("..." if len(str(meta_data)) > 100 else ""))
            else:
                paragraph = segment
                meta_data = None
                log_action(f"段落[{idx+1}]处理模式", "扁平模式 (flat)")
        except Exception as e:
            log_error(f"段落[{idx+1}]解析错误", str(e))
            paragraph = segment
            meta_data = None
            log_action(f"段落[{idx+1}]降级处理", "使用扁平模式 (flat)")
        log_action(f"段落[{idx+1}]专业名词检测", "开始查找匹配术语")
        specific_terms_dict = find_matching_terms(paragraph, terms_dict)
        log_action(f"段落[{idx+1}]专业名词检测完成", f"匹配术语数: {len(specific_terms_dict) if specific_terms_dict else 0}")
        log_action(f"段落[{idx+1}]提示词构造", "开始生成API调用提示词")
        prompt = llm_service.create_prompt(paragraph, specific_terms_dict)
        log_action(f"段落[{idx+1}]提示词构造完成", f"提示词长度: {len(prompt)}")
        try:
            log_action(f"段落[{idx+1}]API调用", "开始调用AI模型API")
            result = llm_service.call_ai_model_api(prompt)
            response = result[0] if isinstance(result, tuple) else result
            log_action(f"段落[{idx+1}]API调用成功", f"响应长度: {len(str(response))}")
            consecutive_failures = 0
            log_action(f"段落[{idx+1}]结果写入", f"模式: {'structured' if preservestructure else 'flat'}")
            if preservestructure:
                write_to_markdown(
                    output_md_file,
                    (response, meta_data),
                    mode='structured'
                )
            else:
                write_to_markdown(output_md_file,
                                (response, meta_data),
                                mode='flat')
            log_action(f"段落[{idx+1}]结果写入完成", output_md_file)
            if task_id in translation_tasks:
                translation_tasks[task_id]["current_paragraph"] = idx + 1
        except Exception as e:
            error_msg = str(e)
            last_error = error_msg
            consecutive_failures += 1
            log_error(f"段落[{idx+1}]API调用失败", f"错误: {error_msg}，连续失败次数: {consecutive_failures}")
            if task_id in translation_tasks:
                translation_tasks[task_id]["status"] = "error"
                translation_tasks[task_id]["error"] = error_msg
            if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                log_action("连续失败阈值触发", f"连续{MAX_CONSECUTIVE_FAILURES}次失败，开始API测试")
                test_results = llm_service.test_api()
                log_action("API测试完成", f"测试结果: {test_results}")
                return {
                    "status": "error",
                    "message": f"连续{MAX_CONSECUTIVE_FAILURES}次翻译失败，已触发API测试",
                    "error": last_error,
                    "test_results": test_results
                }
    if task_id in translation_tasks:
        translation_tasks[task_id]["status"] = "completed"
    log_action("文件处理完成", f"成功生成输出文件: {output_md_file}")
    return {
        "status": "success",
        "output_file": output_md_file
    }

import asyncio
from fastapi.responses import RedirectResponse
from typing import List, Dict

translation_tasks = {}
parameter_cache: List[Dict] = []
MAX_CACHE_SIZE = 10

def add_to_cache(md_filepath: str, nerlist_filepath: str, llm_provider: str) -> str:
    global parameter_cache
    if not os.path.isabs(md_filepath):
        md_filepath = str(UPLOAD_DIR / md_filepath)
    if nerlist_filepath and not os.path.isabs(nerlist_filepath):
        nerlist_filepath = str(UPLOAD_DIR / nerlist_filepath)
    log_action("缓存参数", f"MD文件路径: {md_filepath}, NER列表路径: {nerlist_filepath}, LLM提供商: {llm_provider}")
    cache_item = {
        "md_filepath": md_filepath,
        "nerlist_filepath": nerlist_filepath,
        "llm_provider": llm_provider,
        "timestamp": datetime.now()
    }
    parameter_cache.insert(0, cache_item)
    if len(parameter_cache) > MAX_CACHE_SIZE:
        parameter_cache = parameter_cache[:MAX_CACHE_SIZE]
    return str(0)

def get_from_cache(cache_key: str) -> Dict:
    try:
        index = int(cache_key)
        if 0 <= index < len(parameter_cache):
            return parameter_cache[index]
    except (ValueError, IndexError):
        pass
    return None

@app.get("/editor")
async def editor_page(request: Request, cache_key: str = None):
    log_action("访问编辑器页面", f"客户端: {request.client.host}:{request.client.port}")
    context = {}
    cache_loaded = False
    if cache_key:
        cached_params = get_from_cache(cache_key)
        if cached_params:
            context.update({
                "md_path": cached_params.get("md_filepath"),
                "csv_path": cached_params.get("nerlist_filepath"),
                "llm_provider": cached_params.get("llm_provider")
            })
            log_action("从缓存加载参数", f"缓存键: {cache_key}")
            cache_loaded = True
        else:
            log_error("指定缓存参数未找到", f"缓存键: {cache_key}")
    if not cache_loaded and parameter_cache:
        latest_cache = parameter_cache[0]
        context.update({
            "md_path": latest_cache.get("md_filepath"),
            "csv_path": latest_cache.get("nerlist_filepath"),
            "llm_provider": latest_cache.get("llm_provider")
        })
        log_action("使用最新缓存参数", f"缓存键: {latest_cache.get('cache_key')}")
    return templates.TemplateResponse(request, "editor.html", context)

@app.get("/get-latest-cache")
async def get_latest_cache(request: Request):
    try:
        if parameter_cache:
            latest_cache = parameter_cache[0]
            log_action("获取最新缓存", f"缓存键: {latest_cache.get('cache_key')}")
            return {
                "status": "success",
                "md_path": latest_cache.get("md_filepath", ""),
                "csv_path": latest_cache.get("nerlist_filepath", ""),
                "llm_provider": latest_cache.get("llm_provider", ""),
                "cache_key": latest_cache.get("cache_key", "")
            }
        else:
            return {
                "status": "success",
                "md_path": "",
                "csv_path": "",
                "llm_provider": "",
                "cache_key": ""
            }
    except Exception as e:
        log_error("获取最新缓存失败", str(e))
        return {
            "status": "error",
            "message": str(e)
        }

@app.post("/prepare-editor")
async def prepare_editor(request: Request):
    try:
        data = await request.json()
        md_path = data.get("md_path", "")
        csv_path = data.get("csv_path", "")
        llm_provider = data.get("llm_provider", "")
        cache_key = add_to_cache(md_path, csv_path, llm_provider)
        log_action("准备编辑器配置", f"MD文件: {md_path}, CSV文件: {csv_path}, LLM提供商: {llm_provider}, 缓存键: {cache_key}")
        return {
            "status": "success",
            "cache_key": cache_key,
            "message": "编辑器准备成功"
        }
    except Exception as e:
        log_error("准备编辑器失败", str(e))
        return {
            "status": "error",
            "message": str(e)}

@app.post("/process")
async def process_endpoint(
    md_path: str = Form(...),
    csv_path: str = Form(...),
    llm_provider: str = Form(...)
):
    try:
        log_action("处理API端点调用", "收到处理请求")
        cache_key = add_to_cache(md_path, csv_path, llm_provider)
        log_action("参数已添加到缓存", f"缓存键: {cache_key}")
        return RedirectResponse(
            f"/editor?cache_key={cache_key}",
            status_code=303
        )
    except Exception as e:
        log_error("处理端点异常", str(e))
        return JSONResponse({
            "status": "error",
            "message": "服务器内部错误",
            "error": str(e),
            "test_results": None
        })

@app.get("/load-content")
async def load_content(file_path: str):
    try:
        if not os.path.isabs(file_path):
            file_path = str(UPLOAD_DIR / file_path)
        log_action("加载文件内容", f"文件路径: {file_path}")
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return JSONResponse({
            "status": "success",
            "content": content
        })
    except Exception as e:
        log_error("加载文件内容失败", str(e))
        return JSONResponse({
            "status": "error",
            "message": f"加载文件失败: {str(e)}"
        })

import uuid

@app.post("/start-translation")
async def start_translation(cache_key: str = Form(...)):
    try:
        log_action("开始翻译任务", f"使用缓存键: {cache_key}")
        cached_params = get_from_cache(cache_key)
        if not cached_params:
            raise ValueError("缓存参数未找到")
        md_path = cached_params.get("md_filepath")
        csv_path = cached_params.get("nerlist_filepath")
        llm_provider = cached_params.get("llm_provider")
        log_action("开始翻译任务", f"MD文件: {md_path}, CSV文件: {csv_path}, LLM提供商: {llm_provider}")
        input_dir = os.path.dirname(md_path)
        input_filename = os.path.basename(md_path)
        base_name, extension = os.path.splitext(input_filename)
        output_base_filename = f"{base_name}_output"
        output_md_file = os.path.join(input_dir, f"{output_base_filename}{extension}")
        counter = 1
        while os.path.exists(output_md_file):
            output_md_file = os.path.join(input_dir, f"{output_base_filename}_{counter}{extension}")
            counter += 1
        task_id = os.path.basename(output_md_file)
        translation_tasks[task_id] = {
            "status": "in_progress",
            "current_paragraph": 0,
            "total_paragraphs": 0,
            "output_path": output_md_file,
            "error": None
        }
        asyncio.create_task(run_translation_task(md_path, csv_path, llm_provider, task_id))
        return JSONResponse({
            "status": "success",
            "output_file": output_md_file,
            "task_id": task_id
        })
    except Exception as e:
        log_error("启动翻译任务失败", str(e))
        return JSONResponse({
            "status": "error",
            "message": f"启动翻译任务失败: {str(e)}"
        })

async def run_translation_task(md_path, csv_path, llm_provider, task_id):
    try:
        total_paragraphs = count_structured_paragraphs(md_path, max_chunk_size=global_config.max_chunk_size, preserve_structure=PS)
        if task_id in translation_tasks:
            translation_tasks[task_id]["total_paragraphs"] = total_paragraphs
        result = await asyncio.to_thread(process_files_with_progress, md_path, csv_path, llm_provider, task_id)
        if result.get("status") == "error":
            translation_tasks[task_id]["status"] = "error"
            translation_tasks[task_id]["error"] = result.get("message", "翻译失败")
        else:
            translation_tasks[task_id]["status"] = "completed"
    except Exception as e:
        log_error("翻译任务执行失败", str(e))
        translation_tasks[task_id]["status"] = "error"
        translation_tasks[task_id]["error"] = str(e)

import functools
def process_files_with_progress(input_md_file, csv_file, llm_provider, task_id):
    def update_progress(current, total):
        translation_tasks[task_id]["current_paragraph"] = current
        translation_tasks[task_id]["total_paragraphs"] = total
    original_write = functools.partial(write_to_markdown)
    def write_with_progress(*args, **kwargs):
        result = original_write(*args, **kwargs)
        current = translation_tasks[task_id]["current_paragraph"]
        update_progress(current + 1, translation_tasks[task_id]["total_paragraphs"])
        return result
    return process_files(input_md_file, csv_file, llm_provider)

@app.get("/translation-progress")
async def translation_progress(task_id: str = None, output_file: str = None):
    try:
        task_info = None
        if task_id and task_id in translation_tasks:
            task_info = translation_tasks[task_id]
            output_file = task_info["output_path"]
        elif output_file:
            for tid, task in translation_tasks.items():
                if task["output_path"] == output_file:
                    task_info = task
                    break
        else:
            return JSONResponse({
                "status": "error",
                "message": "必须提供task_id或output_file参数"
            })
        if not task_info:
            return JSONResponse({
                "status": "error",
                "message": "未找到翻译任务"
            })
        content = ""
        if output_file and os.path.exists(output_file):
            try:
                with open(output_file, 'r', encoding='utf-8') as f:
                    content = f.read()
            except Exception as e:
                log_error("读取文件内容失败", str(e))
        progress = 0
        if task_info["total_paragraphs"] > 0:
            progress = int((task_info["current_paragraph"] / task_info["total_paragraphs"]) * 100)
        response = {
            "status": task_info["status"],
            "progress": progress,
            "current_paragraph": task_info["current_paragraph"],
            "total_paragraphs": task_info["total_paragraphs"],
            "content": content
        }
        if task_info["status"] == "error":
            response["message"] = task_info["error"]
        return JSONResponse(response)
    except Exception as e:
        log_error("获取翻译进度失败", str(e))
        return JSONResponse({
            "status": "error",
            "message": f"获取进度失败: {str(e)}"
        })

@app.post("/save-content")
async def save_content(request: Request):
    try:
        data = await request.json()
        file_path = data.get("file_path")
        content = data.get("content")
        if not file_path or content is None:
            return JSONResponse({
                "status": "error",
                "message": "缺少必要参数"
            })
        log_action("保存文件内容", f"文件路径: {file_path}")
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return JSONResponse({
            "status": "success"
        })
    except Exception as e:
        log_error("保存文件内容失败", str(e))
        return JSONResponse({
            "status": "error",
            "message": f"保存失败: {str(e)}"
        })

@app.get("/download")
async def download_file(task_id: str = None, file_path: str = None):
    try:
        if task_id and task_id in translation_tasks:
            task = translation_tasks[task_id]
            file_path = task["output_path"]
            log_action("通过任务ID下载文件", f"任务ID: {task_id}, 文件路径: {file_path}")
        elif file_path:
            log_action("直接下载文件", f"文件路径: {file_path}")
        else:
            return JSONResponse({
                "status": "error",
                "message": "必须提供task_id或file_path参数"
            })
        from fastapi.responses import FileResponse
        return FileResponse(
            path=file_path,
            media_type="application/octet-stream",
            filename=os.path.basename(file_path)
        )
    except Exception as e:
        log_error("下载文件失败", str(e))
        return JSONResponse({
            "status": "error",
            "message": "下载文件失败",
            "error": str(e)
        })

@app.get("/open-file")
async def open_file(task_id: str = None, file_path: str = None):
    try:
        if task_id and task_id in translation_tasks:
            task = translation_tasks[task_id]
            file_path = task["output_path"]
            log_action("通过任务ID打开文件", f"任务ID: {task_id}, 文件路径: {file_path}")
        elif file_path:
            log_action("直接打开文件", f"文件路径: {file_path}")
        else:
            return JSONResponse({
                "status": "error",
                "message": "必须提供task_id或file_path参数"
            })
        from fastapi.responses import FileResponse
        return FileResponse(
            path=file_path,
            media_type="text/markdown",
            filename=os.path.basename(file_path)
        )
    except Exception as e:
        log_error("打开文件失败", str(e))
        return JSONResponse({
            "status": "error",
            "message": "打开文件失败",
            "error": str(e)
        })

@app.post("/test-api")
async def test_api_endpoint(
    llm_provider: str = Form(...)
):
    try:
        log_action("API测试端点调用", f"提供商: {llm_provider}")
        llm_service = LLMService(provider=llm_provider)
        log_action("API测试开始", "执行连接测试")
        test_results = llm_service.test_api()
        log_action("API测试完成", f"结果: {test_results}")
        return JSONResponse({
            "status": "success",
            "test_results": test_results
        })
    except Exception as e:
        log_error("API测试异常", str(e))
        return JSONResponse({
            "status": "error",
            "error": str(e)
        })

def main():
    uvicorn.run(app, host="localhost", port=8008)

if __name__ == "__main__":
    main()
