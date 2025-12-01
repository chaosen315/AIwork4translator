import pandas as pd

def calculate_savings(rag_csv_path, new_csv_path):
    # 读取两个CSV文件
    rag_df = pd.read_csv(rag_csv_path)
    new_df = pd.read_csv(new_csv_path)

    # 合并两个数据表，基于"Input file"
    merged_df = pd.merge(rag_df, new_df, on='Input file', suffixes=('_rag', '_new'))

    # 计算节省的时间和tokens
    merged_df['Time saved'] = merged_df['Taken time_rag'] - merged_df['Taken time_new']
    merged_df['Tokens saved'] = merged_df['Tokens_rag'] - merged_df['Tokens_new']

    # 计算每300个单词节省的时间和tokens
    merged_df['Time saved per 300 words'] = merged_df['Time saved'] * 300 / merged_df['Input len_rag']
    merged_df['Tokens saved per 300 words'] = merged_df['Tokens saved'] * 300 / merged_df['Input len_rag']

    # 计算 token 消耗节省百分比
    merged_df['Token saving percentage'] = (merged_df['Tokens saved'] / merged_df['Tokens_rag']) * 100

    # 计算总体节省情况
    total_time_saved = merged_df['Time saved'].sum()
    total_tokens_saved = merged_df['Tokens saved'].sum()
    total_time_saved_per_300 = total_time_saved * 300 / merged_df['Input len_rag'].sum()
    total_tokens_saved_per_300 = total_tokens_saved * 300 / merged_df['Input len_rag'].sum()
    avg_token_saving_percentage = merged_df['Token saving percentage'].mean()

    # 计算平均值
    avg_time_saved = merged_df['Time saved'].mean()
    avg_tokens_saved = merged_df['Tokens saved'].mean()
    avg_time_saved_per_300 = merged_df['Time saved per 300 words'].mean()
    avg_tokens_saved_per_300 = merged_df['Tokens saved per 300 words'].mean()

    print(f"总节省时间: {total_time_saved:.2f} 秒")
    print(f"总节省tokens: {total_tokens_saved:.0f} tokens")
    print(f"每300个单词总平均节省时间: {total_time_saved_per_300:.2f} 秒")
    print(f"每300个单词总平均节省tokens: {total_tokens_saved_per_300:.0f} tokens")
    print(f"平均 token 节省百分比: {avg_token_saving_percentage:.2f}%")
    print("---")
    print(f"平均每次处理节省时间: {avg_time_saved:.2f} 秒")
    print(f"平均每次处理节省tokens: {avg_tokens_saved:.0f} tokens")
    print(f"每300个单词平均节省时间: {avg_time_saved_per_300:.2f} 秒")
    print(f"每300个单词平均节省tokens: {avg_tokens_saved_per_300:.0f} tokens")

    return merged_df

# 使用函数计算节省情况
rag_csv_path = 'rag_counting_table.csv'
new_csv_path = 'counting_table.csv'

merged_df = calculate_savings(rag_csv_path, new_csv_path)

# 将结果保存到新的CSV文件
merged_df.to_csv('comparison_results.csv', index=False)
print("比较结果已保存到 comparison_results.csv")