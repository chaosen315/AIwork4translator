# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller 打包配置文件
使用方法: pyinstaller build_spec.spec
"""

block_cipher = None

# 收集所有数据文件
import os
import sys

datas = [
    ('static', 'static'),
    ('templates', 'templates'),
    # 注意：data/.env 不打包，应由用户在运行目录自行配置
    ('README.md', '.'),
]

# 添加 magika 模型文件和配置文件（markitdown 依赖）
try:
    import magika
    magika_path = os.path.dirname(magika.__file__)
    models_path = os.path.join(magika_path, 'models')
    config_path = os.path.join(magika_path, 'config')
    
    if os.path.exists(models_path):
        datas.append((models_path, 'magika/models'))
        print(f"✓ 已添加 magika 模型文件: {models_path}")
    
    if os.path.exists(config_path):
        datas.append((config_path, 'magika/config'))
        print(f"✓ 已添加 magika 配置文件: {config_path}")
except ImportError:
    print("⚠ 警告: 未找到 magika，跳过模型文件打包")

# 收集启动脚本（用于双击启动）
import shutil

# 在打包后复制启动脚本到 dist 目录
def copy_launcher_scripts():
    scripts = [
        ('启动-AI翻译工具.sh', '启动-AI翻译工具.sh'),
        ('启动-AI翻译工具.command', '启动-AI翻译工具.command'),
        ('启动-AI翻译工具.bat', '启动-AI翻译工具.bat'),
        ('AI翻译工具.desktop', 'AI翻译工具.desktop'),
    ]
    for src, dst in scripts:
        if os.path.exists(src):
            # 在 COLLECT 阶段会自动处理
            datas.append((src, '.'))
    
copy_launcher_scripts()

# 收集隐藏导入（PyInstaller 可能检测不到的模块）
hiddenimports = [
    'uvicorn.logging',
    'uvicorn.loops',
    'uvicorn.loops.auto',
    'uvicorn.protocols',
    'uvicorn.protocols.http',
    'uvicorn.protocols.http.auto',
    'uvicorn.protocols.websockets',
    'uvicorn.protocols.websockets.auto',
    'uvicorn.lifespan',
    'uvicorn.lifespan.on',
    'openai',
    'google.genai',
    'google.genai.types',
    'pydantic',
    'fastapi',
    'jinja2',
    'markitdown',
    'pandas',
    'aiofiles',
    'magika',
    'magika.magika',
    'onnxruntime',
]

a = Analysis(
    ['launcher.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib',
        'scipy',
        'numpy.distutils',
        'tkinter',
        'test',
        'unittest',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,     # 添加：打包二进制文件
    a.zipfiles,     # 添加：打包 zip 文件
    a.datas,        # 添加：打包数据文件
    [],
    name='AI翻译工具',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # 保留控制台窗口显示日志
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

# 注意：单文件模式不需要 COLLECT
# 所有内容都已打包到上面的 EXE 中
