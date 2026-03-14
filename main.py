from dotenv import load_dotenv
from time import perf_counter
import csv
load_dotenv(dotenv_path="data/.env")
import os, time, json, asyncio
from dataclasses import dataclass, field
from typing import List, Optional, Any, Dict

from modules.config import global_config
from modules.read_tool import read_structured_paragraphs, read_and_process_structured_paragraphs_to_json
from modules.csv_process_tool import get_valid_path, validate_csv_file, load_terms_dict
from modules.terminology_tool import load_glossary_df, save_terms_result
from modules.api_tool import LLMService
from modules.write_out_tool import write_to_markdown, write_to_markdown_through_json, finalize_translation_output, TranslationLogManager
from modules.markitdown_tool import markitdown_tool
from modules.count_tool import count_md_words, count_structured_paragraphs
from modules.translation_core import TranslationCore, TranslationResult, TerminologyPolicy
from modules.export_tool import export_json_to_xlsx, export_json_to_docx, export_json_to_pdf, export_json_to_epub
from services.diagnostics import global_diagnostics

@dataclass
class UserConfig:
    provider: str = ""
    input_md_file: str = ""
    output_md_file: str = ""
    csv_file: str = ""
    merge_in_place: bool = False
    blank_csv_path: str = ""
    enable_concurrency: bool = False
    chunk_size: int = 0
    preserve_structure: bool = False
    input_dir: str = ""
    base_name: str = ""
    extension: str = ""
    json_path: Optional[str] = None
    paragraphs: List[Any] = field(default_factory=list)
    total_paragraphs: int = 0

def get_user_config() -> UserConfig:
    config = UserConfig()
    config.preserve_structure = global_config.preserve_structure
    config.chunk_size = global_config.max_chunk_size
    
    prefs_path = os.path.join("data", ".prefs.json")
    prefs = {}
    if os.path.exists(prefs_path):
        try:
            with open(prefs_path, "r", encoding="utf-8") as f:
                prefs = json.load(f)
        except Exception:
            prefs = {}
            
    # 1. 选择 Provider
    service = LLMService()
    provider_list = list(service.providers.keys())
    provider_str = '","'.join(provider_list)

    while True:
        default_provider = prefs.get("last_provider")
        provider_prompt = f'需要确认API平台（"{provider_str}"）。'
        if default_provider:
            provider_prompt += f"上一次使用{default_provider}，如继续使用请按回车，如有更换请输入："
        else:
            provider_prompt += ": "
        provider_in = input(provider_prompt).strip()
        if not provider_in and default_provider:
            provider_in = default_provider
        
        # 简单验证 Provider 是否有效（可选），这里直接接受
        config.provider = provider_in
        print('')
        
        # 2. 选择文件
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
            
        input_file = input_file.strip('"\'')
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
                    exit(0)
                else:
                    print("输入无效，请输入y或n")
            # config.preserve_structure = False 转换后的文件通常不适合强结构化假设，但已通过一些办法处理
            config.input_md_file = input_md_file
        else:
            config.input_md_file = input_file
        break

    config.input_dir = os.path.dirname(config.input_md_file)
    input_filename = os.path.basename(config.input_md_file)
    config.base_name, config.extension = os.path.splitext(input_filename)
    output_base_filename = f"{config.base_name}_output"
    config.blank_csv_path = os.path.join(config.input_dir, f"{config.base_name}_output_terminology.csv")
    print('')
    
    config.output_md_file = os.path.join(config.input_dir, f"{output_base_filename}{config.extension}")
    counter = 1
    while os.path.exists(config.output_md_file):
        config.output_md_file = os.path.join(config.input_dir, f"{output_base_filename}_{counter}{config.extension}")
        counter += 1

    # 3. 术语表处理
    while True:
        has_glossary = input("您是否已有术语表文件（csv，xlsx）？(y/n): ").strip().lower()
        if has_glossary == 'n':
            with open(config.blank_csv_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(["原文", "译名"])
                writer.writerow(["England", "英格兰"])
            print(f"程序将在翻译结束后生成术语表文件。")
            config.csv_file = config.blank_csv_path
            config.merge_in_place = True # 默认对新生成的表进行合并
            
            # --- 保留 NER 代码片段 (Future Feature) ---
            # 通过实体识别模型提取专业名词生成空白名词表，现阶段为废弃状态
            # print(f'开始调取NER模型...')
            # ... (原有注释代码保留)
            # ----------------------------------------
            break
        elif has_glossary == 'y':
            config.csv_file = get_valid_path("需要术语表文件地址（csv，xlsx）路径: ", validate_csv_file, prefs.get("last_csv_path"))
            merge_choice = input("是否将新术语合并到术语表？(y/n): ").strip().lower()
            config.merge_in_place = (merge_choice == 'y')
            if not config.merge_in_place:
                print(f"新术语会作为新的术语表保存到与输入文件相同的目录下。")
            break
        else:
            print("输入无效，请输入y或n")

    # 4. 并发选择与预处理
    concurrency_choice = input("是否启用并发模式？(y/n): ").strip().lower()
    config.enable_concurrency = (concurrency_choice == 'y')

    print(f"开始翻译文档...")
    if config.enable_concurrency:
        print("已启用并发模式。正在预处理文档...")
        config.json_path = read_and_process_structured_paragraphs_to_json(
            config.input_md_file, 
            max_chunk_size=config.chunk_size, 
            min_chunk_size=int(config.chunk_size*0.5),
            preserve_structure=config.preserve_structure
        )
        print(f"文档预处理完成，中间文件已保存至: {config.json_path}")
        with open(config.json_path, 'r', encoding='utf-8') as f:
            json_data = json.load(f)
        config.paragraphs = json_data['text_info']
        config.total_paragraphs = len(config.paragraphs)
        print(f"文档总段落数为【{config.total_paragraphs}】（已合并短段落）")
    else:
        config.total_paragraphs = count_structured_paragraphs(config.input_md_file, max_chunk_size=config.chunk_size, preserve_structure=config.preserve_structure)
        print(f"文档总段落数为【{config.total_paragraphs}】")
        print(f"开始调取文档段落...")
        config.paragraphs = read_structured_paragraphs(config.input_md_file, max_chunk_size=config.chunk_size, preserve_structure=config.preserve_structure) # pyright: ignore[reportAttributeAccessIssue]

    return config

async def run_translation_loop(paragraphs, translation_core: TranslationCore, terms_dict, aggregated_new_terms, output_md_file, PS, json_path=None):
    # Ensure paragraphs are sorted
    paragraphs.sort(key=lambda x: x['paragraph_number'] if isinstance(x, dict) and 'paragraph_number' in x else 0)
    
    # 1. Replay logs and filter completed tasks
    if json_path:
        log_manager = TranslationLogManager(json_path)
        updates = await asyncio.to_thread(log_manager.replay_logs)
        if updates:
            print(f"[System] 发现 {len(updates)} 个已完成的段落记录，正在恢复进度...")
            for p in paragraphs:
                p_id = p.get('paragraph_number')
                if p_id in updates:
                    # Update paragraph with logged info
                    info = updates[p_id]
                    p['translation'] = info.get('translation', '')
                    p['notes'] = info.get('notes', '')
                    p['new_terms'] = info.get('new_terms', [])
                    p['status'] = 'completed'
                    
                    # Restore terms to aggregated list for consistency
                    if p['new_terms']:
                        aggregated_new_terms.extend(p['new_terms'])
    
    queue = asyncio.Queue()
    for p in paragraphs:
        if p.get('status') != 'completed':
            queue.put_nowait(p)
        
    file_lock = asyncio.Lock()
    tracker_state = {'next_id': 1} if json_path else None
    stats = {'total_tokens': 0}
    aggregated_new_terms_dict = {}
    for nt in list(aggregated_new_terms):
        k = str(nt.get('term', '')).strip()
        if k:
            aggregated_new_terms_dict[k] = nt
    
    consecutive_failures = 0
    
    async def worker(worker_id):
        nonlocal consecutive_failures
        print(f"[System] Worker-{worker_id} 启动")
        while True:
            # 检查全局错误状态或连续失败次数
            is_err, _ = global_diagnostics.get_global_error_state()
            if is_err or consecutive_failures >= int(os.getenv('MAX_RETRIES', 3)) + 2:
                if not is_err:
                     print(f"[System] 监测到连续失败次数过多 ({consecutive_failures})，停止所有任务。")
                     global_diagnostics.set_global_error_state(True, "Too many consecutive failures")
                break

            try:
                segment = queue.get_nowait()
            except asyncio.QueueEmpty:
                print(f"[System] Worker-{worker_id} 队列为空，准备退出")
                break
            
            try:
                p_id = segment.get('paragraph_number', '?') if isinstance(segment, dict) else '?'
                print(f"[System] Worker-{worker_id} 取出段落 {p_id} (队列剩余: {queue.qsize()})")
                
                # 调用核心
                result = await translation_core.execute_translation_step(
                    segment, terms_dict, aggregated_new_terms_dict, 
                    tracker_state=tracker_state,
                    terminology_policy=TerminologyPolicy.MERGE_ON_CONFLICT
                )
                
                if not result.success:
                    consecutive_failures += 1
                    print(f"[System] Worker-{worker_id} 段落 {p_id} 失败: {result.error}")
                    # 触发诊断
                    asyncio.create_task(safe_api_diagnostics(translation_core.llm_service))
                    # 注意：这里不要调用 queue.task_done()，统一由 finally 处理
                    continue

                # 成功则重置连续失败计数
                consecutive_failures = 0
                stats['total_tokens'] += result.tokens
                
                
                
                # 写入
                async with file_lock:
                    aggregated_new_terms.extend(result.new_terms_delta)
                    for nt in result.new_terms_delta:
                        k = str(nt.get('term', '')).strip()
                        v = str(nt.get('translation', '')).strip()
                        if k:
                            aggregated_new_terms_dict[k] = v
                    
                    response_text = result.content
                    if result.notes:
                        response_text += f"\n\n---\n\n{result.notes}\n"
                    
                    mode = 'structured' if PS else 'flat'
                    if json_path and tracker_state:
                        content_info = {
                            'translation': result.content,
                            'notes': result.notes,
                            'new_terms': result.new_terms_delta,
                            'matched_terms': result.matched_terms_delta # Added missing field
                        }
                        # Use updated logic: just append log, no MD writing here
                        await asyncio.to_thread(write_to_markdown_through_json, json_path, output_md_file, p_id, content_info, tracker_state, mode) # type: ignore
                    else:
                        # Fallback for non-JSON mode (still direct write)
                        await asyncio.to_thread(write_to_markdown, output_md_file, (response_text, segment.get('meta_data')), mode) # type: ignore
                
                print(f"[System] Worker-{worker_id} 完成段落 {p_id}")

            except Exception as e:
                consecutive_failures += 1
                print(f"[System] Error in Worker-{worker_id} processing segment: {e}")
                asyncio.create_task(safe_api_diagnostics(translation_core.llm_service))
            finally:
                queue.task_done()

    concurrency_limit = min(int(os.getenv('Currency_Limit', 5)), int(os.getenv('Requests_Per_Minute', 10)))
    print(f"[System] 初始化并发工作池，Worker数量: {concurrency_limit}")
    workers = [asyncio.create_task(worker(i+1)) for i in range(concurrency_limit)]
    await asyncio.gather(*workers)

    # 熔断后尝试保存未翻译部分 (Log based recovery makes this less critical but kept for non-JSON mode)
    is_err, _ = global_diagnostics.get_global_error_state()
    if is_err:
        print("[System] 任务因熔断停止。")
        # Logic to save rest.md could reuse finalize if implemented, but here we just stop.
        # Log is already saved.
    
    # Finalize Output
    if json_path and not is_err: # Only finalize if no global error? Or always?
        # User might want partial result. Let's finalize even if error, so we get what we have.
        print("[System] 正在生成最终 Markdown 文件...")
        mode = 'structured' if PS else 'flat'
        await asyncio.to_thread(finalize_translation_output, json_path, output_md_file, mode)
        print(f"[System] 最终文件生成完毕: {output_md_file}")

    return stats['total_tokens']

async def safe_api_diagnostics(llm_service: LLMService):
    try:
        # 检查是否已有全局错误
        is_err, _ = global_diagnostics.get_global_error_state()
        if is_err:
            return # 已有错误，不再重复诊断

        print("\n[System] 检测到任务失败，正在进行非阻塞 API 诊断...")
        # 运行诊断
        results = await asyncio.to_thread(llm_service.test_api)
        
        if not results.get("success"):
            error_msg = f"API Diagnostics Failed: {results.get('error')}"
            global_diagnostics.set_global_error_state(True, error_msg)
            print(f"[System] 诊断发现问题: {error_msg}")
            # 这里可以扩展：写入日志文件
        else:
            print("[System] API 诊断通过，可能是临时网络波动或内容问题。")
            
    except Exception as e:
        print(f"[System] 诊断过程本身出错: {e}")

def run_sync_translation_loop(config: UserConfig, translation_core: TranslationCore, terms_dict, aggregated_new_terms, glossary_df):
    total_token = 0
    current_paragraph = 0
    concurrency_api_failures = 0
    
    # 转换 aggregated_new_terms (list) 到 dict 供 Core 使用
    # 在同步循环中，我们可以维护一个 persistent dict 以提高效率
    # 因为是串行的，所以是安全的
    
    # 初始化 persistent dict
    persistent_new_terms_dict = {}
    
    iterator = config.paragraphs
    # 如果是 generator (read_structured_paragraphs 返回 generator)，需要小心
    # config.paragraphs 在非并发模式下是 generator
    
    # Collection for export
    completed_paragraphs = []
    
    for segment in iterator:
        current_paragraph += 1
        print(f"开始翻译段落【{current_paragraph}】/【{config.total_paragraphs}】")
        
        # 适配 segment
        if isinstance(segment, dict) and 'content' in segment:
            paragraph_text = segment['content']
            meta_data = segment['meta_data']
        elif config.preserve_structure:
            paragraph_text, meta_data = segment
        else:
            paragraph_text = segment
            meta_data = None
            
        # 构造临时的 segment dict 供 Core 使用
        segment_data = {
            "content": paragraph_text,
            "meta_data": meta_data
        }
        
        while True: # Retry loop for interactive recovery
            # 更新 persistent_new_terms_dict
            for nt in aggregated_new_terms:
                k = str(nt.get('term', '')).strip()
                if k:
                    persistent_new_terms_dict[k] = nt
            
            try:
                # 同步循环调用异步方法，需要 asyncio.run 或者在新事件循环中运行
                # 但 main 已经是 sync 的。为了复用 Core (Async)，我们需要 wrap 一下
                # 或者 TranslationCore 可以提供同步入口？
                # 由于 Core 内部用了 asyncio.to_thread，它是 async 的。
                # 我们可以在这里用 asyncio.run 单次运行
                
                result = asyncio.run(translation_core.execute_translation_step(
                    segment_data, 
                    terms_dict, 
                    persistent_new_terms_dict,
                    terminology_policy=TerminologyPolicy.MERGE_ON_CONFLICT
                ))
                
                if not result.success:
                    # 失败处理
                    raise Exception(result.error)
                
                # 成功
                aggregated_new_terms.extend(result.new_terms_delta)
                total_token += result.tokens
                
                response_text = result.content
                if result.notes:
                    response_text += f"\n\n---\n\n{result.notes}\n"
                print(response_text)
                
                # 收集用于 JSON 导出的数据
                completed_paragraphs.append({
                    'paragraph_number': current_paragraph,
                    'meta_data': meta_data,
                    'content': paragraph_text,
                    'translation': result.content,
                    'notes': result.notes,
                    'new_terms': result.new_terms_delta,
                    'matched_terms': result.matched_terms_delta,
                    'status': 'completed'
                })
                
                # 写出
                mode = 'structured' if config.preserve_structure else 'flat'
                write_to_markdown(config.output_md_file, (response_text, meta_data), mode) # type: ignore
                
                print(f"已处理第{current_paragraph}段内容，输出已保存到：")
                print(config.output_md_file)
                concurrency_api_failures = 0
                break # Next paragraph
                
            except KeyboardInterrupt:
                raise # Let outer handler catch it
            except Exception as e:
                concurrency_api_failures += 1
                print(f"\nAPI调用失败：{str(e)}")
                print(f"连续翻译失败次数: {concurrency_api_failures}/{os.getenv('MAX_RETRIES', 3)}")
                
                if concurrency_api_failures >= int(os.getenv('MAX_RETRIES', 3)):
                    # 交互式恢复
                    print(f"\n连续失败，开始API测试...")
                    # 这里的 test_api 是 sync 的 (in LLMService)，但 TranslationCore 里没暴露 sync 的 test_api
                    # 直接用 llm_service
                    try:
                        test_results = translation_core.llm_service.test_api()
                        print(f"测试结果: {test_results}")
                        if isinstance(test_results, dict) and test_results.get("success"):
                            choice = input("API测试通过。是否重试当前段落？(y/n): ").strip().lower()
                            if choice == 'y':
                                concurrency_api_failures = 0
                                continue
                            else:
                                raise KeyboardInterrupt # Trigger save and exit
                        else:
                            print("API测试失败。")
                            raise KeyboardInterrupt
                    except Exception as test_e:
                        print(f"测试出错: {test_e}")
                        raise KeyboardInterrupt
                else:
                    print("正在重试当前段落...")
                    time.sleep(1) # Backoff

    # Save JSON for Sync Mode
    if not config.json_path:
        config.json_path = os.path.join(config.input_dir, f"{config.base_name}_intermediate.json")
    
    try:
        with open(config.json_path, 'w', encoding='utf-8') as f:
            json.dump({'text_info': completed_paragraphs}, f, ensure_ascii=False, indent=2)
        print(f"中间 JSON 文件已保存至: {config.json_path}")
    except Exception as e:
        print(f"保存中间 JSON 失败: {e}")

    return total_token

def save_untranslated(input_md_file, input_dir, base_name, last_text=None):
    if not last_text:
        return
    try:
        keyword = last_text[:20]
        with open(input_md_file, 'r', encoding='utf-8') as f:
            original_content = f.read()
        idx = original_content.find(keyword)
        if idx != -1:
            untranslated_part = original_content[idx:]
            untranslated_path = os.path.join(input_dir, f"{base_name}_rest.md")
            with open(untranslated_path, 'w', encoding='utf-8') as uf:
                uf.write(untranslated_part)
            print(f"未翻译部分已保存至：{untranslated_path}")
    except Exception as e:
        print(f"保存未翻译部分失败: {e}")

def handle_export(config: UserConfig):
    if not config.json_path or not os.path.exists(config.json_path):
        print("未找到中间 JSON 文件，无法进行格式转换导出。")
        return

    print("\n--------------------------------------------------")
    print("翻译已完成。是否需要将结果导出为其他格式？")
    print("支持格式：DOCX, PDF, EPUB, XLSX")
    print("--------------------------------------------------")
    
    while True:
        choice = input("是否导出？(y/n): ").strip().lower()
        if choice == 'n':
            return
        elif choice == 'y':
            break
        else:
            print("请输入 y 或 n")
    
    print("\n请选择导出格式（输入数字，多选可用逗号分隔，如 1,4）：")
    print("1. DOCX (Word 文档)")
    print("2. PDF (便携式文档)")
    print("3. EPUB (电子书)")
    print("4. XLSX (Excel 表格)")
    print("5. 全部导出")
    
    choices = input("请输入选项: ").strip()
    selected = set()
    
    if '5' in choices or 'all' in choices.lower():
        selected = {1, 2, 3, 4}
    else:
        parts = choices.replace('，', ',').split(',')
        for p in parts:
            p = p.strip()
            if p in ('1', '2', '3', '4'):
                selected.add(int(p))
    
    if not selected:
        print("未选择有效格式，跳过导出。")
        return

    base_path = os.path.splitext(config.output_md_file)[0]
    
    if 1 in selected:
        print("正在导出 DOCX ...")
        out_path = f"{base_path}.docx"
        if export_json_to_docx(config.json_path, out_path):
            print(f"DOCX 导出成功: {out_path}")
            
    if 2 in selected:
        print("正在导出 PDF ...")
        out_path = f"{base_path}.pdf"
        if export_json_to_pdf(config.json_path, out_path):
            print(f"PDF 导出成功: {out_path}")

    if 3 in selected:
        print("正在导出 EPUB ...")
        out_path = f"{base_path}.epub"
        if export_json_to_epub(config.json_path, out_path):
            print(f"EPUB 导出成功: {out_path}")

    if 4 in selected:
        print("正在导出 XLSX ...")
        out_path = f"{base_path}.xlsx"
        if export_json_to_xlsx(config.json_path, out_path):
            print(f"XLSX 导出成功: {out_path}")
            
    print("导出流程结束。")

def finalize_process(config: UserConfig, total_token, start_time, glossary_df, aggregated_new_terms):
    end_time = perf_counter()
    time_taken = end_time - start_time
    print(time.strftime('共耗时：%H时%M分%S秒', time.gmtime(int(time_taken))))
    
    # Save terms
    new_glossary_path = save_terms_result(config.merge_in_place, glossary_df, aggregated_new_terms, config.csv_file, config.blank_csv_path)
    print("新的术语表已保存：")
    print(new_glossary_path)
    print("译文文件已保存：")
    print(config.output_md_file)
    # Save Prefs
    prefs_path = os.path.join("data", ".prefs.json")
    new_prefs = {
        "last_provider": config.provider,
        "last_input_md_file": config.input_md_file,
        "last_csv_path": config.csv_file,
    }
    try:
        os.makedirs("data", exist_ok=True)
        with open(prefs_path, "w", encoding="utf-8") as f:
            json.dump(new_prefs, f, ensure_ascii=False, indent=2)
    except Exception:
        pass
        
    # Counting table
    if os.path.exists(config.output_md_file):
        raw_len = count_md_words(config.input_md_file)
        processed_len = count_md_words(config.output_md_file)
        new_row = [str(config.input_md_file), raw_len, str(config.output_md_file), processed_len, total_token, time_taken]
        file_exists = os.path.isfile('counting_table.csv') and os.path.getsize('counting_table.csv') > 0
        with open('counting_table.csv','a',newline='',encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            if not file_exists:
                writer.writerow(['Input file','Input len','Output file','Output len','Tokens','Taken time'])
            writer.writerow(new_row)

def main():
    try:
        config = get_user_config()
    except KeyboardInterrupt:
        print("\n用户取消配置，程序退出。")
        return

    start_time = perf_counter()
    terms_dict = load_terms_dict(config.csv_file)
    glossary_df = load_glossary_df(config.csv_file)
    aggregated_new_terms = []
    
    llm_service = LLMService(provider=config.provider)
    translation_core = TranslationCore(llm_service)
    
    total_token = 0
    
    try:
        if config.enable_concurrency:
            total_token = asyncio.run(run_translation_loop(
                config.paragraphs, 
                translation_core, 
                terms_dict, 
                aggregated_new_terms, 
                config.output_md_file, 
                config.preserve_structure, 
                config.json_path
            ))
        else:
            total_token = run_sync_translation_loop(
                config, 
                translation_core, 
                terms_dict, 
                aggregated_new_terms, 
                glossary_df
            )
            
        finalize_process(config, total_token, start_time, glossary_df, aggregated_new_terms)
        
        handle_export(config)
        
    except KeyboardInterrupt:
        print("\n任务已中断，开始保存累积的术语表……")
        new_glossary_path = save_terms_result(config.merge_in_place, glossary_df, aggregated_new_terms, config.csv_file, config.blank_csv_path)
        print(f"新的术语表已保存：{new_glossary_path}")
        # 保存未翻译部分 (仅针对同步模式或能获取最后位置的情况，这里做个简单尝试)
        # 这里的 save_untranslated 需要 last_text，但 main 里拿不到。
        # 可以在 run_sync_translation_loop 里处理了，这里只是兜底。
        return

if __name__ == "__main__":
    main()
