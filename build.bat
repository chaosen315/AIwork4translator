@echo off
REM Windows 打包脚本
chcp 65001 >nul

echo ======================================
echo   AI 翻译工具 - 开始打包
echo ======================================

REM 检查 PyInstaller 是否安装
pyinstaller --version >nul 2>&1
if errorlevel 1 (
    echo 未找到 PyInstaller，正在安装...
    pip install pyinstaller
)

REM 清理之前的构建
echo 清理旧的构建文件...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

REM 开始打包
echo 开始打包应用...
pyinstaller build_spec.spec

if %errorlevel% == 0 (
    echo.
    echo ======================================
    echo   打包完成！（单文件模式）
    echo ======================================
    
    REM 复制启动脚本和说明文件到 dist 目录
    echo.
    echo 正在复制启动脚本和说明文件...
    copy /Y 启动-AI翻译工具.sh dist\ >nul
    copy /Y 启动-AI翻译工具.command dist\ >nul
    copy /Y 启动-AI翻译工具.bat dist\ >nul
    copy /Y AI翻译工具.desktop dist\ >nul
    echo 文件复制完成
    
    echo.
    echo 可执行文件位置: dist\
    echo.
    echo 运行方式:
    echo   方式1（推荐）: cd dist 后双击 启动-AI翻译工具.bat（显示日志）
    echo   方式2: cd dist 后双击 AI翻译工具.exe
    echo.
    echo 注意事项:
    echo 0. 单文件模式：所有依赖已打包到可执行文件中（~100MB）
    echo 1. 首次运行会在同目录创建 .env 配置文件模板
    echo 2. 运行前需在 .env 文件中配置 API 密钥
    echo 3. uploads\ 和 output_files\ 目录会自动创建
    echo 4. 分发时只需提供: AI翻译工具.exe + 启动脚本 + 使用说明.txt
    echo 5. 首次启动稍慢（解压内部文件），后续会快一些
    echo 6. 建议使用 启动-AI翻译工具.bat 来启动，可以看到日志
    echo.
    pause
) else (
    echo.
    echo 打包失败，请检查错误信息
    pause
    exit /b 1
)
