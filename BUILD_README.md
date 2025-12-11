# 打包指南

## 环境要求

- **Python 版本**: 3.12.x
- **操作系统**: Linux / macOS / Windows
- **必需工具**: PyInstaller

> **重要**: 本项目打包需要 Python 3.12，请确保使用正确的 Python 版本进行打包。PyInstaller暂时不支持3.13.*

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
- **目录**: `dist/`
- **主程序**: 
  - Linux/macOS: `dist/AI翻译工具`（单文件，约 100MB）
  - Windows: `dist/AI翻译工具.exe`（单文件，约 100MB）
- **启动脚本**:
  - Linux: `dist/启动-AI翻译工具.sh`
  - macOS: `dist/启动-AI翻译工具.command`
  - Windows: `dist/启动-AI翻译工具.bat`
  - Linux Desktop: `dist/AI翻译工具.desktop`

## 打包配置说明

### build_spec.spec 文件
- `datas`: 包含的静态文件（templates、static、magika 模型和配置等）
- `hiddenimports`: 手动指定的隐藏导入（包括 magika、onnxruntime 等）
- `excludes`: 排除不需要的大型库（减小文件大小）

### 关键依赖说明

#### Magika 文件识别（用于 PDF/Word 等文档转换）
```python
# 自动包含 magika 的模型和配置文件
import magika
magika_path = os.path.dirname(magika.__file__)
datas.append((os.path.join(magika_path, 'models'), 'magika/models'))
datas.append((os.path.join(magika_path, 'config'), 'magika/config'))
```

打包时会包含：
- `magika/models/` - 机器学习模型文件（约 3MB）
- `magika/config/content_types_kb.min.json` - 文件类型配置（44KB）

### 当前配置：单文件模式

当前 `build_spec.spec` 使用单文件打包模式：
- **优点**: 
  - 只有一个可执行文件，分发简单
  - 用户无需关心依赖目录结构
  - 双击启动脚本即可运行
- **缺点**: 
  - 首次启动时解压到临时目录（`/tmp/_MEI*`），稍慢
  - 文件较大（约 100MB）

配置关键代码：
```python
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,  # 所有二进制库
    a.zipfiles,  # 压缩文件
    a.datas,     # 数据文件
    [],
    name='AI翻译工具',
    console=True,  # 显示控制台（用于日志输出）
)
# 无 COLLECT - 单文件模式
```

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

#### 切换到目录模式（可选）
如果想使用目录模式（启动更快，但有 `_internal` 文件夹），修改 `build_spec.spec`：

```python
# 修改 EXE 部分
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,  # 关键：分离二进制文件
    name='AI翻译工具',
    console=True,
)

# 添加 COLLECT 部分
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='AI翻译工具'
)
```

## 分发注意事项

### 分发包结构（单文件模式）
```
分发包/
├── AI翻译工具(.exe)           # 主程序（100MB，包含所有依赖）
├── 启动-AI翻译工具.sh         # Linux 启动脚本
├── 启动-AI翻译工具.command    # macOS 启动脚本
├── 启动-AI翻译工具.bat        # Windows 启动脚本
├── AI翻译工具.desktop         # Linux 桌面快捷方式
└── 使用说明.txt              # 用户文档
```

### 用户系统要求
- **无需安装 Python**：所有依赖已打包在可执行文件中
- **操作系统**: 
  - Linux: 任何主流发行版（64位）
  - Windows: Windows 7 或更高版本（64位）
  - macOS: macOS 10.13 或更高版本
- **必需软件**: 
  - 浏览器（Chrome、Firefox、Edge 等）
  - 终端/命令行（用于查看日志）

### 首次运行
1. 双击对应平台的启动脚本（会打开终端显示日志）
2. 程序自动创建 `.env` 配置文件
3. 浏览器自动打开 http://127.0.0.1:8000
4. 在设置页面填写 API 密钥

### .env 配置文件
程序首次运行会在可执行文件同目录创建 `.env` 模板：
```env
# API 配置（至少配置一个）
KIMI_API_KEY=
OPENAI_API_KEY=
DEEPSEEK_API_KEY=
GEMINI_API_KEY=

# 其他配置
SYSTEM_LANGUAGE=zh-CN
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

### Q3: PDF/Word 转换失败，报错 "model dir not found"
**原因**: magika 模型或配置文件未正确打包
**解决**: 确认 `build_spec.spec` 包含以下配置：
```python
import magika
magika_path = os.path.dirname(magika.__file__)
datas.append((os.path.join(magika_path, 'models'), 'magika/models'))
datas.append((os.path.join(magika_path, 'config'), 'magika/config'))

hiddenimports = [
    'magika',
    'magika.magika',
    'onnxruntime',
    # ... 其他导入
]
```

### Q4: 静态文件找不到
**解决**: 检查 `datas` 配置，确保路径正确

### Q5: 程序体积太大
**解决**: 
1. 添加更多排除项到 `excludes`
2. 使用虚拟环境打包（只包含必要依赖）
3. 启用 UPX 压缩

### Q5: 程序体积太大
**解决**: 
1. 添加更多排除项到 `excludes`
2. 使用虚拟环境打包（只包含必要依赖）
3. 考虑切换到目录模式（体积相近，但无需每次解压）

**体积参考**:
- 单文件模式: ~100MB（包含 Python 解释器 + 所有库 + magika 模型）
- 目录模式: ~100MB（分散在多个文件中，启动更快）

### Q6: 启动慢或首次启动卡顿
**原因**: 单文件模式会解压到临时目录 `/tmp/_MEI*`
**解决**: 
- 正常现象，首次启动后会更快
- 如需最快启动速度，可切换到目录模式

### Q7: 双击可执行文件没有显示日志
**解决**: 使用提供的启动脚本（`.sh`、`.command`、`.bat`），它们会打开终端显示日志

## 测试清单

打包完成后，测试以下功能：
- [ ] 程序正常启动（双击启动脚本）
- [ ] 终端显示日志输出
- [ ] 浏览器自动打开 http://127.0.0.1:8000
- [ ] 上传 MD 文件
- [ ] 上传 PDF/Word/Excel 文件（测试 magika 转换）
- [ ] 上传 CSV 词典
- [ ] API 连接测试
- [ ] 翻译功能
- [ ] 文件下载
- [ ] .env 配置文件自动创建

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
