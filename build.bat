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
    echo   打包完成！
    echo ======================================
    echo.
    echo 可执行文件位置: dist\AI翻译工具\
    echo.
    echo 运行方式:
    echo   1. 进入 dist\AI翻译工具 目录
    echo   2. 双击运行 AI翻译工具.exe
    echo.
    echo 注意事项:
    echo 1. 首次运行前需在 data\.env 中配置 API 密钥
    echo 2. uploads\ 和 output_files\ 目录会自动创建
    echo 3. 可以将整个 'AI翻译工具' 文件夹分发给其他用户
    echo.
    pause
) else (
    echo.
    echo 打包失败，请检查错误信息
    pause
    exit /b 1
)
