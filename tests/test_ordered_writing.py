
import unittest
import json
import os
import shutil
from unittest.mock import patch, MagicMock
from modules.write_out_tool import write_to_markdown_through_json

class TestOrderedWriting(unittest.TestCase):
    def setUp(self):
        self.test_dir = r"d:\BaiduSyncdisk\桌游\program_translator\tests\temp_data"
        os.makedirs(self.test_dir, exist_ok=True)
        self.json_path = os.path.join(self.test_dir, "test_ordered.json")
        self.md_path = os.path.join(self.test_dir, "output.md")
        
        # Create initial JSON
        self.data = {
            'text_info': [
                {
                    'paragraph_number': 1,
                    'content': 'p1',
                    'meta_data': {},
                    'translation': '',
                    'notes': '',
                    'new_terms': [],
                    'status': 'pending'
                },
                {
                    'paragraph_number': 2,
                    'content': 'p2',
                    'meta_data': {},
                    'translation': '',
                    'notes': '',
                    'new_terms': [],
                    'status': 'pending'
                },
                {
                    'paragraph_number': 3,
                    'content': 'p3',
                    'meta_data': {},
                    'translation': '',
                    'notes': '',
                    'new_terms': [],
                    'status': 'pending'
                }
            ]
        }
        with open(self.json_path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False)
            
    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
        
    @patch('modules.write_out_tool.write_to_markdown')
    def test_out_of_order_writing(self, mock_write):
        tracker = {'next_id': 1}
        
        # 1. Complete Paragraph 2 (Out of order)
        info_2 = {'translation': 't2', 'notes': 'n2', 'new_terms': []}
        write_to_markdown_through_json(self.json_path, self.md_path, 2, info_2, tracker)
        
        # Verify JSON updated
        with open(self.json_path, 'r', encoding='utf-8') as f:
            d = json.load(f)
            self.assertEqual(d['text_info'][1]['translation'], 't2')
            self.assertEqual(d['text_info'][1]['status'], 'completed')
            
        # Verify NO write to MD (waiting for 1)
        mock_write.assert_not_called()
        self.assertEqual(tracker['next_id'], 1)
        
        # 2. Complete Paragraph 1
        info_1 = {'translation': 't1', 'notes': '', 'new_terms': []}
        write_to_markdown_through_json(self.json_path, self.md_path, 1, info_1, tracker)
        
        # Verify writes
        # Should write p1 THEN p2
        self.assertEqual(mock_write.call_count, 2)
        
        # Check calls args
        # Call 1: p1
        args1, _ = mock_write.call_args_list[0]
        self.assertEqual(args1[1][0], 't1') # content tuple (text, meta)
        
        # Call 2: p2
        args2, _ = mock_write.call_args_list[1]
        self.assertIn('t2', args2[1][0])
        self.assertIn('n2', args2[1][0])
        
        self.assertEqual(tracker['next_id'], 3)
        
        # 3. Complete Paragraph 3
        info_3 = {'translation': 't3', 'notes': '', 'new_terms': []}
        write_to_markdown_through_json(self.json_path, self.md_path, 3, info_3, tracker)
        
        self.assertEqual(mock_write.call_count, 3)
        self.assertEqual(tracker['next_id'], 4)

if __name__ == '__main__':
    unittest.main()
