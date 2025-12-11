#!/bin/bash
# Linux/macOS 打包脚本

echo "======================================"
echo "  AI 翻译工具 - 开始打包"
echo "======================================"

# 检查 PyInstaller 是否安装
if ! command -v pyinstaller &> /dev/null; then
    echo "未找到 PyInstaller，正在安装..."
    pip install pyinstaller
fi

# 清理之前的构建
echo "清理旧的构建文件..."
rm -rf build dist

# 开始打包
echo "开始打包应用..."
pyinstaller build_spec.spec

if [ $? -eq 0 ]; then
    echo ""
    echo "======================================"
    echo "  打包完成！"
    echo "======================================"
    echo ""
    echo "可执行文件位置: dist/AI翻译工具/"
    echo ""
    echo "运行方式:"
    echo "  cd dist/AI翻译工具"
    echo "  ./AI翻译工具"
    echo ""
    echo "注意事项:"
    echo "1. 首次运行前需在 data/.env 中配置 API 密钥"
    echo "2. uploads/ 和 output_files/ 目录会自动创建"
    echo "3. 可以将整个 'AI翻译工具' 文件夹分发给其他用户"
else
    echo ""
    echo "打包失败，请检查错误信息"
    exit 1
fi
