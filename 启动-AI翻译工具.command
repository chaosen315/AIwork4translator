#!/bin/bash
# macOS 启动脚本 - 双击即可运行

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# 在 Terminal.app 中运行
echo "========================================="
echo "  AI 翻译工具"
echo "========================================="
echo ""

./AI翻译工具

# 保持窗口打开
echo ""
echo "按任意键退出..."
read -n 1
