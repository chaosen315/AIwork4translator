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

def test_xlsx_with_extra_columns():
    """测试包含额外列（如reason）的XLSX文件"""
    
    # 创建包含额外列的测试数据（3列）
    test_data = {
        'col1': ['A', 'B', 'C'],
        'col2': ['1', '2', '3'],
        'reason': ['reason1', 'reason2', 'reason3']
    }
    
    # 创建临时XLSX文件
    with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp_xlsx:
        df = pd.DataFrame(test_data)
        df.to_excel(tmp_xlsx.name, index=False)
        xlsx_path = tmp_xlsx.name
    
    try:
        print(f"\n创建多列测试XLSX文件: {xlsx_path}")
        
        # 测试验证函数
        is_valid, updated_path = validate_csv_file(xlsx_path)
        
        print(f"验证结果: {is_valid}")
        print(f"路径: {updated_path}")
        
        if is_valid:
            print("✓ 多列XLSX文件被正确接受")
            # 验证CSV内容是否保留了第三列
            if os.path.exists(updated_path):
                df_res = pd.read_csv(updated_path)
                if len(df_res.columns) >= 3:
                     print(f"✓ 转换后的CSV包含 {len(df_res.columns)} 列，额外列已保留")
                     # 检查列名是否重命名正确
                     # 现在的逻辑是前两列重命名为 term, translation，后面的保留
                     if df_res.columns[0] == 'term' and df_res.columns[1] == 'translation':
                         print("✓ 前两列列名已正确标准化")
                     else:
                         print(f"✗ 列名未标准化: {df_res.columns.tolist()}")
                else:
                    print(f"✗ 转换后的CSV丢失了列，仅有 {len(df_res.columns)} 列")
                os.remove(updated_path)
        else:
            print("✗ 多列XLSX文件被错误拒绝")
            
    finally:
        # 清理测试文件
        if os.path.exists(xlsx_path):
            os.remove(xlsx_path)
            print(f"清理测试文件: {xlsx_path}")

def test_really_invalid_xlsx():
    """测试真正的无效XLSX文件（少于2列）"""
    
    test_data = {
        'col1': ['A', 'B', 'C']
    }
    
    with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp_xlsx:
        df = pd.DataFrame(test_data)
        df.to_excel(tmp_xlsx.name, index=False)
        xlsx_path = tmp_xlsx.name
        
    try:
        print(f"\n创建单列测试XLSX文件: {xlsx_path}")
        is_valid, updated_path = validate_csv_file(xlsx_path)
        
        if not is_valid:
            print("✓ 单列XLSX文件正确被拒绝")
        else:
            print("✗ 单列XLSX文件被错误接受")
            if updated_path and updated_path != xlsx_path and os.path.exists(updated_path):
                os.remove(updated_path)
    finally:
        if os.path.exists(xlsx_path):
            os.remove(xlsx_path)
            print(f"清理测试文件: {xlsx_path}")

if __name__ == "__main__":
    print("=== 测试XLSX转换功能 ===")
    test_xlsx_conversion()
    
    print("\n=== 测试多列XLSX保留功能 ===")
    test_xlsx_with_extra_columns()
    
    print("\n=== 测试无效列数XLSX ===")
    test_really_invalid_xlsx()
    
    print("\n=== 测试完成 ===")
