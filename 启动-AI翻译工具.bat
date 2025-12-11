@echo off
REM Windows 启动脚本 - 双击即可在新窗口运行
chcp 65001 >nul
title AI 翻译工具

REM 切换到脚本所在目录
cd /d "%~dp0"

echo ========================================
echo   AI 翻译工具
echo ========================================
echo.

REM 运行主程序
"AI翻译工具.exe"

REM 如果程序异常退出，保持窗口打开
if errorlevel 1 (
    echo.
    echo 程序已退出，请检查错误信息
    echo.
    pause
)
