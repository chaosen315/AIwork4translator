#!/bin/bash
# AI翻译工具启动脚本 - 自动打开终端窗口

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 检测可用的终端模拟器
if command -v gnome-terminal &> /dev/null; then
    # GNOME Terminal
    gnome-terminal -- bash -c "cd '$SCRIPT_DIR' && ./AI翻译工具; echo ''; echo '按任意键退出...'; read -n 1"
elif command -v kgx &> /dev/null; then
    # Gnome Console (kgx)
    kgx -- bash -c "cd '$SCRIPT_DIR' && ./AI翻译工具; echo ''; echo '按任意键退出...'; read -n 1"
elif command -v xfce4-terminal &> /dev/null; then
    # XFCE4 Terminal
    xfce4-terminal --hold -e bash -c "cd '$SCRIPT_DIR' && ./AI翻译工具"
elif command -v konsole &> /dev/null; then
    # KDE Konsole
    konsole --hold -e bash -c "cd '$SCRIPT_DIR' && ./AI翻译工具"
elif command -v xterm &> /dev/null; then
    # xterm
    xterm -hold -e bash -c "cd '$SCRIPT_DIR' && ./AI翻译工具"
elif command -v x-terminal-emulator &> /dev/null; then
    # Debian/Ubuntu 通用终端
    x-terminal-emulator -e bash -c "cd '$SCRIPT_DIR' && ./AI翻译工具; echo ''; echo '按任意键退出...'; read -n 1"
else
    # 如果没有找到图形终端，尝试在当前终端运行
    echo "未找到图形终端模拟器，在当前终端运行..."
    ./AI翻译工具
fi
