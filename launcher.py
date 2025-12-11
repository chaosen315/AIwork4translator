#!/usr/bin/env python3
"""
应用启动器 - 用于打包后的可执行文件
自动启动 Web 服务器并打开浏览器
"""
import sys
import os
import webbrowser
import threading
import time
import signal
from pathlib import Path

def get_resource_path(relative_path):
    """获取资源文件的绝对路径（支持 PyInstaller 打包后的环境）"""
    try:
        # PyInstaller 创建临时文件夹，路径存储在 _MEIPASS 中
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def setup_environment():
    """设置运行环境"""
    # 确保必要的目录存在
    for dir_name in ['uploads', 'output_files', 'input_files', 'data']:
        os.makedirs(dir_name, exist_ok=True)
    
    # 如果 .env 不存在，在当前目录创建模板
    env_path = Path('.env')
    if not env_path.exists():
        env_path.write_text("""PRESERVE_STRUCTURE=True
MAX_CHUNK_SIZE=2000
MAX_RETRIES=6
# 如果每分钟请求数上限被设为 0 或负值，相当于“不限流”
Requests_Per_Minute=10

SYSTEM_PROMPT="你是态度专业的翻译专家,擅长分析长难句并给出周到且语气自然的译作。术语表是你的助力工具：你借助它确保译名统一,若遇到未提供对应译名的术语,为新名词确定译名,在译注中讲述理由。并在translation中保持GitHub风格Markdown结构（标题、列表、图片链接等）。严格执行结构化输出：仅返回JSON对象,无任何额外文字。字段：translation（中文正文,使用术语表译名）、notes（列表,逐条说明新术语的选择理由或典故）、newterminology（数组,元素包含term、translation、reason）。"
BASE_PROMPT="在完成翻译主职，准确应用术语表提供的术语译名之外，不放过任何没有出现在术语表里的专有术语（人名、地名、组织缩写、生造词等）。若术语表未给出对应译名(尤其是人名和标题),一定要在translation中使用新译名,notes列表说明新译名的注释,newterminology记录新译名的取名过程。仅返回合法JSON。请以JSON结构输出翻译结果（json）：{\"translation\": \"...\",\"notes\": [\"术语1：注释\",\"术语2：注释\"],\"newterminology\": [{\"term\": \"...\", \"translation\": \"...\", \"reason\": \"...\"}]}。"

########################
# LLM Providers
########################
#  kimi的模型默认值为kimi-k2-turbo-preview
KIMI_BASE_URL=https://api.moonshot.cn/v1
KIMI_API_KEY=YOUR_KIMI_API_KEY
KIMI_MODEL=kimi-k2-turbo-preview

# gpt的模型默认值为gpt-realtime
OPENAI_API_KEY="your_openai_api_key" # 如果使用自定义URL，需要自行拼接密钥的完整格式
OPENAI_BASE_URL="https://api.openai.com/v1" # 测试功能：可以使用自定义URL
GPT_MODEL="gpt-realtime"

# 深seek的模型默认值为deepseek-chat
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
DEEPSEEK_API_KEY=YOUR_DEEPSEEK_API_KEY
DEEPSEEK_MODEL=deepseek-chat

# 硅流的模型默认值为deepseek-ai/DeepSeek-V3.1-Terminus
SILLICON_BASE_URL="https://api.siliconflow.cn/v1/chat/completions"
SILLICON_API_KEY="YOUR_SILLICON_API_KEY"
SILLICON_MODEL="deepseek-ai/DeepSeek-V3.1-Terminus"
SILLICON_JSON_URL="https://api.siliconflow.cn/v1"
SILLICON_JSON_MODEL="moonshotai/Kimi-K2-Instruct-0905"

# 谷歌的模型默认值为gemini-2.5-flash
GEMINI_API_KEY="YOUR_GEMINI_API_KEY" # 如果使用自定义URL，需要自行拼接密钥的完整格式
GEMINI_BASE_URL=None # 测试功能：可以使用自定义URL
GEMINI_MODEL=gemini-2.5-flash

# 豆包的模型默认值为doubao-seed-1-6-251015，暂不支持使用
DOUBAO_BASE_URL=https://ark.cn-beijing.volces.com/api/v3
DOUBAO_API_KEY=YOUR_DOUBAO_API_KEY
DOUBAO_MODEL=doubao-seed-1-6-251015

########################
# Local Models (Ollama)
########################
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=your-model-name
""")
        print(f"已创建配置文件模板: {env_path.absolute()}")

def open_browser():
    """延迟打开浏览器"""
    time.sleep(2)  # 等待服务器启动
    webbrowser.open('http://127.0.0.1:8000')
    print("浏览器已打开，访问地址: http://127.0.0.1:8000")

def main():
    """主函数"""
    print("=" * 60)
    print("  AI 翻译工具 - 启动中...")
    print("=" * 60)
    
    setup_environment()
    
    # 在后台线程中打开浏览器
    browser_thread = threading.Thread(target=open_browser, daemon=True)
    browser_thread.start()
    
    # 启动 FastAPI 应用
    print("\n正在启动 Web 服务器...")
    print("按 Ctrl+C 退出应用\n")
    print("-" * 60)
    
    try:
        import uvicorn
        from app import app
        
        # 运行服务器 - 启用日志输出到控制台
        uvicorn.run(
            app,
            host="127.0.0.1",
            port=8000,
            log_level="info",
            access_log=True,  # 启用访问日志
            log_config={
                "version": 1,
                "disable_existing_loggers": False,
                "formatters": {
                    "default": {
                        "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                    },
                },
                "handlers": {
                    "default": {
                        "formatter": "default",
                        "class": "logging.StreamHandler",
                        "stream": "ext://sys.stdout",
                    },
                },
                "loggers": {
                    "uvicorn": {"handlers": ["default"], "level": "INFO"},
                },
            }
        )
    except KeyboardInterrupt:
        print("\n\n应用已停止")
    except Exception as e:
        print(f"\n错误: {e}")
        print("\n请检查:")
        print("1. data/.env 文件中的 API 配置是否正确")
        print("2. 是否有其他程序占用了 8000 端口")
        input("\n按 Enter 键退出...")
        sys.exit(1)

if __name__ == "__main__":
    main()
