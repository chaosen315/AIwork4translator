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
    echo "  打包完成！（单文件模式）"
    echo "======================================"
    
    # 复制启动脚本和说明文件到 dist 目录
    echo ""
    echo "正在复制启动脚本和说明文件..."
    cp 启动-AI翻译工具.sh dist/
    cp 启动-AI翻译工具.command dist/
    cp 启动-AI翻译工具.bat dist/
    cp AI翻译工具.desktop dist/
    chmod +x dist/启动-AI翻译工具.sh
    chmod +x dist/启动-AI翻译工具.command
    chmod +x dist/AI翻译工具
    echo "文件复制完成"
    
    # 显示文件大小
    echo ""
    echo "打包结果:"
    ls -lh dist/ | grep -E "AI翻译工具|启动"
    
    echo ""
    echo "可执行文件位置: dist/"
    echo ""
    echo "运行方式:"
    echo "  方式1（推荐）: cd dist && 双击 启动-AI翻译工具.sh（显示日志）"
    echo "  方式2: cd dist && ./AI翻译工具（在终端运行）"
    echo ""
    echo "注意事项:"
    echo "0. 单文件模式：所有依赖已打包到可执行文件中（97MB）"
    echo "1. 首次运行会在同目录创建 .env 配置文件模板"
    echo "2. 运行前需在 .env 文件中配置 API 密钥"
    echo "3. uploads/ 和 output_files/ 目录会自动创建"
    echo "4. 分发时只需提供: AI翻译工具 + 启动脚本 + 使用说明.txt"
    echo "5. 首次启动稍慢（解压内部文件），后续会快一些"
else
    echo ""
    echo "打包失败，请检查错误信息"
    exit 1
fi
