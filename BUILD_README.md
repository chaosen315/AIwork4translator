# 打包指南

## 环境要求

- **Python 版本**: 3.12.x
- **操作系统**: Linux / macOS / Windows
- **必需工具**: PyInstaller

> **重要**: 本项目需要 Python 3.12，请确保使用正确的 Python 版本进行打包。

## 快速开始

### Linux/macOS
```bash
chmod +x build.sh
./build.sh
```

### Windows
双击运行 `build.bat` 或在命令行执行：
```cmd
build.bat
```

## 详细说明

### 1. 确认 Python 版本
```bash
python --version  # 应显示 Python 3.12.x
```

### 2. 安装依赖
```bash
pip install pyinstaller
```

### 2. 打包命令
```bash
pyinstaller build_spec.spec
```

### 3. 输出位置
打包完成后，可执行文件在：
- **目录**: `dist/AI翻译工具/`
- **主程序**: 
  - Linux/macOS: `AI翻译工具`
  - Windows: `AI翻译工具.exe`

## 打包配置说明

### build_spec.spec 文件
- `datas`: 包含的静态文件（templates、static等）
- `hiddenimports`: 手动指定的隐藏导入
- `excludes`: 排除不需要的大型库（减小文件大小）

### 优化选项

#### 减小体积
```python
excludes=[
    'matplotlib',
    'scipy',
    'numpy.distutils',
    'tkinter',
    'test',
    'unittest',
]
```

#### 单文件模式（可选）
如果想打包成单个 exe 文件，修改 `build_spec.spec`：
```python
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,  # 添加
    a.zipfiles,  # 添加
    a.datas,     # 添加
    [],
    name='AI翻译工具',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    onefile=True,  # 关键：启用单文件模式
)

# 删除 COLLECT 部分
```

## 分发注意事项

### 必须包含的文件/目录
```
dist/AI翻译工具/
├── AI翻译工具(.exe)     # 主程序
├── static/              # 静态资源
├── templates/           # HTML 模板
├── data/               
│   └── .env            # 配置文件（需用户填写 API 密钥）
├── uploads/            # 自动创建
└── output_files/       # 自动创建
```

### 首次运行配置
用户需要在 `data/.env` 中配置：
```env
KIMI_API_KEY=sk-xxx...
OPENAI_API_KEY=sk-xxx...
```

## 常见问题

### Q1: Python 版本不匹配
**问题**: 使用了错误的 Python 版本进行打包
**解决**: 
```bash
# 检查 Python 版本
python --version

# 如果版本不是 3.12.x，请使用正确的 Python
python3.12 --version
python3.12 -m pip install pyinstaller
python3.12 -m PyInstaller build_spec.spec
```

### Q2: 打包后运行报错 "No module named 'xxx'"
**解决**: 在 `build_spec.spec` 的 `hiddenimports` 中添加缺失的模块

### Q3: 静态文件找不到
**解决**: 检查 `datas` 配置，确保路径正确

### Q4: 程序体积太大
**解决**: 
1. 添加更多排除项到 `excludes`
2. 使用虚拟环境打包（只包含必要依赖）
3. 启用 UPX 压缩

### Q5: 启动慢
**解决**: 
- 单文件模式会解压到临时目录，启动较慢
- 使用目录模式（当前配置）启动更快

## 测试清单

打包完成后，测试以下功能：
- [ ] 程序正常启动
- [ ] 浏览器自动打开
- [ ] 上传 MD 文件
- [ ] 上传 CSV 词典
- [ ] API 连接测试
- [ ] 翻译功能
- [ ] 文件下载

## 平台特定说明

### Linux
- 打包后的程序可能需要 `chmod +x` 添加执行权限
- 某些发行版可能需要额外安装 `libffi` 等库

### Windows
- 杀毒软件可能误报，需添加白名单
- 可以使用 `--icon` 参数添加自定义图标

### macOS
- 可能需要在"系统偏好设置 > 安全性与隐私"中允许运行
- 考虑使用 `py2app` 代替 PyInstaller（可选）

## 进阶：创建安装程序

### Windows - 使用 Inno Setup
1. 安装 Inno Setup
2. 创建安装脚本引用 `dist/AI翻译工具/` 目录
3. 生成安装包 `.exe`

### Linux - 创建 .deb 或 .rpm
使用 `fpm` 工具打包

### macOS - 创建 .dmg
使用 `create-dmg` 工具
