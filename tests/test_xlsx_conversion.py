#!/usr/bin/env python3
"""
测试XLSX文件转换为CSV的功能
"""

import os
import pandas as pd
import tempfile
from modules.csv_process_tool import validate_csv_file

def test_xlsx_conversion():
    """测试XLSX文件转换为CSV的功能"""
    
    # 创建测试数据
    test_data = {
        'term': ['Artificial Intelligence', 'Machine Learning', 'Deep Learning'],
        'definition': ['人工智能', '机器学习', '深度学习']
    }
    
    # 创建临时XLSX文件
    with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp_xlsx:
        df = pd.DataFrame(test_data)
        df.to_excel(tmp_xlsx.name, index=False)
        xlsx_path = tmp_xlsx.name
    
    try:
        print(f"创建测试XLSX文件: {xlsx_path}")
        
        # 测试验证函数
        is_valid, updated_path = validate_csv_file(xlsx_path)
        
        print(f"验证结果: {is_valid}")
        print(f"更新后的路径: {updated_path}")
        
        if is_valid:
            print("✓ XLSX文件验证成功并转换为CSV格式")
            
            # 检查转换后的CSV文件是否存在
            if os.path.exists(updated_path):
                print(f"✓ 转换后的CSV文件存在: {updated_path}")
                
                # 读取并验证CSV内容
                with open(updated_path, 'r', encoding='utf-8-sig') as f:
                    content = f.read()
                    print("CSV文件内容:")
                    print(content)
                    
                    # 验证内容是否正确
                    if 'Artificial Intelligence' in content and '人工智能' in content:
                        print("✓ CSV内容验证成功")
                    else:
                        print("✗ CSV内容验证失败")
                        
                # 清理转换后的文件
                os.remove(updated_path)
            else:
                print("✗ 转换后的CSV文件不存在")
        else:
            print("✗ XLSX文件验证失败")
            
    finally:
        # 清理原始XLSX文件
        if os.path.exists(xlsx_path):
            os.remove(xlsx_path)
            print(f"清理测试文件: {xlsx_path}")

def test_invalid_xlsx():
    """测试格式不正确的XLSX文件"""
    
    # 创建格式不正确的测试数据（3列而不是2列）
    test_data = {
        'col1': ['A', 'B', 'C'],
        'col2': ['1', '2', '3'],
        'col3': ['x', 'y', 'z']
    }
    
    # 创建临时XLSX文件
    with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp_xlsx:
        df = pd.DataFrame(test_data)
        df.to_excel(tmp_xlsx.name, index=False)
        xlsx_path = tmp_xlsx.name
    
    try:
        print(f"\n创建无效格式测试XLSX文件: {xlsx_path}")
        
        # 测试验证函数
        is_valid, updated_path = validate_csv_file(xlsx_path)
        
        print(f"验证结果: {is_valid}")
        print(f"路径: {updated_path}")
        
        if not is_valid:
            print("✓ 无效格式的XLSX文件正确被拒绝")
        else:
            print("✗ 无效格式的XLSX文件被错误接受")
            
    finally:
        # 清理测试文件
        if os.path.exists(xlsx_path):
            os.remove(xlsx_path)
            print(f"清理测试文件: {xlsx_path}")

if __name__ == "__main__":
    print("=== 测试XLSX转换功能 ===")
    test_xlsx_conversion()
    
    print("\n=== 测试无效XLSX文件 ===")
    test_invalid_xlsx()
    
    print("\n=== 测试完成 ===")