#!/usr/bin/env python3
"""
仿真测试脚本 - 直接调用modules工具测试提示词效果
模拟真实翻译流程，用于验证和调优提示词
"""

import os
import sys
import json
import csv
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from datetime import datetime
import time
from dotenv import load_dotenv

# 加载环境变量
load_dotenv(dotenv_path="data/.env")

# 导入项目模块
from modules.api_tool import LLMService
from modules.csv_process_tool import load_terms_dict, find_matching_terms
from modules.read_tool import read_structured_paragraphs
from modules.config import global_config

class TranslationSimulator:
    """翻译仿真器 - 模拟真实翻译流程"""
    
    def __init__(self, provider: str = "kimi"):
        self.llm_service = LLMService(provider=provider)
        self.provider = provider
        self.test_dir = Path(__file__).parent
        self.results_dir = self.test_dir / "simulation_results"
        self.results_dir.mkdir(exist_ok=True)
        
        # 测试文件路径
        self.samples_file = self.test_dir / "test_samples.md"
        self.terms_file = self.test_dir / "test_terms.csv"
        
        # 统计信息
        self.total_segments = 0
        self.successful_segments = 0
        self.total_tokens = 0
        self.format_compliant_segments = 0
        
    def load_test_data(self) -> Tuple[List[Dict], Dict[str, str]]:
        """加载测试数据和术语词典"""
        print("📂 加载测试数据...")
        
        # 加载样例
        samples = []
        if self.samples_file.exists():
            with open(self.samples_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # 按标题分割样例
            sections = content.split('\n## ')
            for section in sections[1:]:  # 跳过第一个标题
                lines = section.split('\n')
                title = lines[0].strip()
                text = '\n'.join(lines[1:]).strip()
                if text:
                    samples.append({
                        'title': title,
                        'text': text,
                        'id': len(samples) + 1
                    })
        
        # 加载术语词典
        terms_dict = {}
        if self.terms_file.exists():
            terms_dict = load_terms_dict(str(self.terms_file))
        
        print(f"✅ 加载完成：{len(samples)} 个样例，{len(terms_dict)} 个术语")
        return samples, terms_dict
    
    def simulate_translation_process(self, text: str, terms_dict: Dict[str, str], 
                                   sample_id: int, title: str) -> Dict:
        """模拟完整的翻译流程"""
        print(f"\n🔄 处理样例 {sample_id}: {title}")
        print(f"原文长度: {len(text)} 字符")
        
        # 模拟段落分割（按实际流程）
        segments = self._split_into_segments(text)
        print(f"分割为 {len(segments)} 个段落")
        
        segment_results = []
        aggregated_new_terms = []
        
        for seg_idx, segment in enumerate(segments, 1):
            print(f"\n📄 翻译段落 {seg_idx}/{len(segments)}")
            
            # 查找匹配的术语（模拟真实流程）
            specific_terms = find_matching_terms(segment, terms_dict)
            if specific_terms:
                print(f"发现 {len(specific_terms)} 个匹配术语")
            
            # 创建提示词（使用实际的create_prompt方法）
            prompt = self.llm_service.create_prompt(segment, specific_terms)
            
            # 调用API
            try:
                response_obj, tokens = self.llm_service.call_ai_model_api(prompt)
                print(type(response_obj))
                print(response_obj)
                self.total_tokens += tokens
                self.successful_segments += 1

                translation = response_obj.get('translation', '')
                notes = response_obj.get('notes', '')
                print(type(notes))
                new_terms = response_obj.get('newterminology', [])
                aggregated_new_terms.extend(new_terms)
                joined = "\n\n---\n\n".join([translation, notes])

                print(f"✅ 翻译成功 (tokens: {tokens})")

                # 分析输出格式
                format_analysis = self._analyze_output_format(joined)

                segment_results.append({
                    'segment_id': seg_idx,
                    'original': segment,
                    'translation_joined': joined,
                    'translation': translation,
                    'notes': notes,
                    'newterminology': new_terms,
                    'tokens': tokens,
                    'format_analysis': format_analysis,
                    'success': True
                })

                # 显示结果预览
                self._display_translation_preview(joined, format_analysis)
                
            except Exception as e:
                print(f"❌ 翻译失败: {str(e)}")
                segment_results.append({
                    'segment_id': seg_idx,
                    'original': segment,
                    'translation': '',
                    'tokens': 0,
                    'format_analysis': {},
                    'success': False,
                    'error': str(e)
                })
            
            self.total_segments += 1
        
        return {
            'sample_id': sample_id,
            'title': title,
            'original_text': text,
            'segments': segment_results,
            'total_segments': len(segments),
            'successful_segments': sum(1 for seg in segment_results if seg['success']),
            'new_terms_total': len(aggregated_new_terms)
        }
    
    def _split_into_segments(self, text: str) -> List[str]:
        """模拟段落分割逻辑"""
        # 使用与真实流程类似的逻辑
        max_size = global_config.max_chunk_size
        
        # 首先尝试按双换行分割
        paragraphs = text.split('\n\n')
        segments = []
        current_segment = ""
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
                
            # 如果段落本身就很长，需要进一步分割
            if len(para) > max_size:
                # 按句子分割
                sentences = para.replace('. ', '.\n').replace('! ', '!\n').replace('? ', '?\n').split('\n')
                for sentence in sentences:
                    sentence = sentence.strip()
                    if len(sentence) > max_size:
                        # 如果句子还太长，按字符数强制分割
                        for i in range(0, len(sentence), max_size):
                            chunk = sentence[i:i+max_size]
                            if chunk:
                                segments.append(chunk)
                    elif sentence:
                        segments.append(sentence)
            else:
                # 检查是否可以将当前段落添加到现有段
                if len(current_segment) + len(para) < max_size and current_segment:
                    current_segment += "\n\n" + para
                else:
                    if current_segment:
                        segments.append(current_segment)
                    current_segment = para
        
        if current_segment:
            segments.append(current_segment)
        
        return segments
    
    def _analyze_output_format(self, joined_text: str) -> Dict:
        analysis = {
            'has_main_text': False,
            'has_footnotes': False,
            'format_correct': False,
            'main_text': '',
            'footnotes': '',
            'issues': []
        }
        if not joined_text:
            analysis['issues'].append('翻译结果为空')
            return analysis
        text = joined_text.replace('\r\n', '\n').strip()
        parts = None
        if '\n\n---\n\n' in text:
            parts = text.split('\n\n---\n\n', 1)
        elif '\n---\n' in text:
            parts = text.split('\n---\n', 1)
        else:
            lines = text.split('\n')
            sep_idx = -1
            for i, line in enumerate(lines):
                if line.strip() == '---':
                    sep_idx = i
                    break
            if sep_idx != -1:
                parts = ['\n'.join(lines[:sep_idx]), '\n'.join(lines[sep_idx+1:])]
        if parts:
            main_text = parts[0].strip()
            footnotes = parts[1].strip()
            analysis['main_text'] = main_text
            analysis['footnotes'] = footnotes
            analysis['has_main_text'] = bool(main_text)
            analysis['has_footnotes'] = bool(footnotes)
            bullet = any(l.strip().startswith('-') for l in footnotes.splitlines())
            analysis['format_correct'] = analysis['has_main_text'] and analysis['has_footnotes'] and bullet
            if not bullet:
                analysis['issues'].append('译注未使用列表格式')
        else:
            analysis['main_text'] = text
            analysis['has_main_text'] = True
            analysis['issues'].append('未找到分隔符 ---')
        return analysis
    
    def _display_translation_preview(self, translation: str, format_analysis: Dict):
        """显示翻译结果预览"""
        if format_analysis.get('format_correct', False):
            print("✅ 格式合规 - 双段式输出")
            main_text = format_analysis.get('main_text', '')
            footnotes = format_analysis.get('footnotes', '')
            print(f"正文预览: {main_text[:100]}...")
            if footnotes:
                print(f"译注预览: {footnotes[:100]}...")
        else:
            print("❌ 格式不合规")
            issues = format_analysis.get('issues', [])
            if issues:
                print(f"问题: {', '.join(issues)}")
            print(f"输出预览: {translation[:150]}...")
    
    def run_simulation(self) -> None:
        """运行完整的仿真测试"""
        print(f"\n{'='*80}")
        print(f"🚀 开始翻译仿真测试 - 使用 {self.provider.upper()} 提供商")
        print(f"{'='*80}")
        
        start_time = time.time()
        
        # 加载测试数据
        samples, terms_dict = self.load_test_data()
        
        if not samples:
            print("❌ 没有可用的测试样例")
            return
        
        simulation_results = []
        
        # 对每个样例进行仿真
        for sample in samples:
            result = self.simulate_translation_process(
                sample['text'], terms_dict, sample['id'], sample['title']
            )
            simulation_results.append(result)
            
            # 更新统计
            for seg in result['segments']:
                if seg['success'] and seg['format_analysis'].get('format_correct', False):
                    self.format_compliant_segments += 1
        
        # 生成报告
        self._generate_simulation_report(simulation_results, start_time)
        
        # 保存详细结果
        self._save_simulation_results(simulation_results)
    
    def _generate_simulation_report(self, results: List[Dict], start_time: float) -> None:
        """生成仿真测试报告"""
        print(f"\n{'='*80}")
        print("📊 仿真测试报告")
        print(f"{'='*80}")
        
        total_samples = len(results)
        successful_samples = sum(1 for r in results if r['successful_segments'] > 0)
        
        print(f"测试样例数: {total_samples}")
        print(f"成功样例数: {successful_samples}")
        print(f"总段落数: {self.total_segments}")
        print(f"成功翻译段落: {self.successful_segments}")
        print(f"格式合规段落: {self.format_compliant_segments}")
        print(f"总tokens消耗: {self.total_tokens}")
        
        if self.total_segments > 0:
            print(f"翻译成功率: {self.successful_segments/self.total_segments*100:.1f}%")
            print(f"格式合规率: {self.format_compliant_segments/self.total_segments*100:.1f}%")
        
        if self.successful_segments > 0:
            print(f"平均每段tokens: {self.total_tokens/self.successful_segments:.0f}")
        
        print(f"总耗时: {time.time() - start_time:.2f}秒")
        
        # 详细分析
        print(f"\n{'='*40}")
        print("详细样例分析:")
        print(f"{'='*40}")
        
        for result in results:
            print(f"\n📄 {result['title']}")
            print(f"  总段落: {result['total_segments']}")
            print(f"  成功段落: {result['successful_segments']}")
            
            # 统计格式合规情况
            compliant_segments = sum(
                1 for seg in result['segments'] 
                if seg['success'] and seg['format_analysis'].get('format_correct', False)
            )
            if result['successful_segments'] > 0:
                print(f"  格式合规: {compliant_segments}/{result['successful_segments']}")
    
    def _save_simulation_results(self, results: List[Dict]) -> None:
        """保存仿真结果"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 保存JSON格式
        json_file = self.results_dir / f"simulation_{self.provider}_{timestamp}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump({
                'provider': self.provider,
                'timestamp': timestamp,
                'summary': {
                    'total_samples': len(results),
                    'total_segments': self.total_segments,
                    'successful_segments': self.successful_segments,
                    'format_compliant_segments': self.format_compliant_segments,
                    'total_tokens': self.total_tokens
                },
                'results': results
            }, f, ensure_ascii=False, indent=2)
        
        # 保存可读格式
        txt_file = self.results_dir / f"simulation_{self.provider}_{timestamp}.txt"
        with open(txt_file, 'w', encoding='utf-8') as f:
            f.write(f"翻译仿真测试报告\n")
            f.write(f"提供商: {self.provider}\n")
            f.write(f"时间: {timestamp}\n")
            f.write(f"{'='*80}\n\n")
            
            for result in results:
                f.write(f"样例: {result['title']}\n")
                f.write(f"原文: {result['original_text'][:200]}...\n\n")
                
                for seg in result['segments']:
                    if seg['success']:
                        f.write(f"段落 {seg['segment_id']}:\n")
                        f.write(f"原文: {seg['original'][:100]}...\n")
                        f.write(f"译文: {seg['translation'][:100]}...\n")
                        
                        analysis = seg['format_analysis']
                        if analysis.get('format_correct', False):
                            f.write(f"格式: ✅ 合规\n")
                            f.write(f"正文: {analysis.get('main_text', '')[:100]}...\n")
                            f.write(f"译注: {analysis.get('footnotes', '')[:100]}...\n")
                        else:
                            f.write(f"格式: ❌ 不合规\n")
                            if analysis.get('issues'):
                                f.write(f"问题: {', '.join(analysis['issues'])}\n")
                        f.write("\n")
                f.write(f"{'='*40}\n\n")
        
        print(f"\n💾 结果已保存:")
        print(f"  JSON格式: {json_file}")
        print(f"  文本格式: {txt_file}")

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='翻译提示词仿真测试工具')
    parser.add_argument('--provider', default='kimi', 
                       choices=['kimi', 'deepseek', 'gpt', 'silicon', 'gemini', 'doubao'],
                       help='选择LLM提供商')
    parser.add_argument('--sample', type=int, help='只测试指定编号的样例')
    
    args = parser.parse_args()
    
    # 创建仿真器并运行
    simulator = TranslationSimulator(provider=args.provider)
    
    if args.sample:
        # 测试指定样例
        samples, terms_dict = simulator.load_test_data()
        if 0 < args.sample <= len(samples):
            sample = samples[args.sample - 1]
            result = simulator.simulate_translation_process(
                sample['text'], terms_dict, sample['id'], sample['title']
            )
            simulator._generate_simulation_report([result], time.time())
        else:
            print(f"❌ 样例编号无效，有效范围: 1-{len(samples)}")
    else:
        # 运行完整仿真
        simulator.run_simulation()

if __name__ == "__main__":
    main()
