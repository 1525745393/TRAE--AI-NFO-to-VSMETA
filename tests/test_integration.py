"""
集成测试 - 测试 NFO to VSMETA 转换器的主要功能
"""
import os
import tempfile
import json
import unittest
from unittest.mock import patch, MagicMock


class TestIntegration(unittest.TestCase):
    """集成测试套件"""

    def setUp(self):
        """测试前设置"""
        self.test_dir = tempfile.TemporaryDirectory()
        self.test_path = self.test_dir.name

    def tearDown(self):
        """测试后清理"""
        self.test_dir.cleanup()

    def test_config_load_save(self):
        """测试配置加载和保存（集成）"""
        try:
            from nfo_to_vsmeta_converter_complete import Config
            
            # 创建配置
            config = Config()
            config.report_output_dir = os.path.join(self.test_path, "output")
            
            # 保存配置
            config_file = os.path.join(self.test_path, "config.json")
            config.save_to_file(config_file)
            
            # 验证配置文件存在
            self.assertTrue(os.path.exists(config_file))
            
            # 加载配置
            loaded_config = Config.from_file(config_file)
            
            # 验证配置正确加载
            self.assertEqual(loaded_config.report_output_dir, config.report_output_dir)
            
        except Exception as e:
            self.fail(f"Config load/save failed: {e}")

    def test_plugin_manager_basic_flow(self):
        """测试插件管理器基本工作流"""
        try:
            from nfo_to_vsmeta_converter_complete import PluginManager
            
            # 创建插件管理器
            plugin_dir = os.path.join(self.test_path, "plugins")
            os.makedirs(plugin_dir, exist_ok=True)
            
            manager = PluginManager()
            
            # 验证初始化
            self.assertIsNotNone(manager)
            self.assertEqual(len(manager._plugins), 0)
            
        except Exception as e:
            self.fail(f"Plugin manager test failed: {e}")

    def test_basic_file_operations(self):
        """测试基本文件操作"""
        # 创建测试文件
        test_file = os.path.join(self.test_path, "test.txt")
        with open(test_file, "w") as f:
            f.write("test content")
        
        # 验证文件创建
        self.assertTrue(os.path.exists(test_file))
        
        # 验证文件内容
        with open(test_file, "r") as f:
            content = f.read()
            self.assertEqual(content, "test content")

    @patch('builtins.input', side_effect=['y', 'n'])
    def test_interactive_flow_simulation(self, mock_input):
        """模拟交互式流程（不实际运行 GUI）"""
        # 这个测试验证我们可以导入和访问必要的类
        try:
            from nfo_to_vsmeta_converter_complete import Config
            
            # 测试配置创建
            config = Config()
            self.assertIsNotNone(config)
            
        except Exception as e:
            self.fail(f"Interactive flow test failed: {e}")

    def test_directory_operations(self):
        """测试目录操作"""
        # 创建子目录
        subdir = os.path.join(self.test_path, "subdir1", "subdir2")
        os.makedirs(subdir, exist_ok=True)
        
        # 验证目录创建
        self.assertTrue(os.path.exists(subdir))
        self.assertTrue(os.path.isdir(subdir))

    def test_json_operations(self):
        """测试 JSON 操作（与元数据处理相关）"""
        test_data = {
            "title": "Test Video",
            "year": 2024,
            "rating": 8.5,
            "genres": ["Action", "Sci-Fi"]
        }
        
        json_file = os.path.join(self.test_path, "metadata.json")
        
        # 保存 JSON
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(test_data, f)
        
        # 验证保存
        self.assertTrue(os.path.exists(json_file))
        
        # 加载 JSON
        with open(json_file, "r", encoding="utf-8") as f:
            loaded_data = json.load(f)
        
        # 验证加载数据
        self.assertEqual(loaded_data, test_data)

    def test_module_imports(self):
        """测试所有主要模块可以成功导入"""
        modules_to_test = [
            ("nfo_to_vsmeta_converter_complete", ["Config", "PluginManager"]),
            ("web_ui", ["app"])
        ]
        
        for module_name, objects in modules_to_test:
            try:
                module = __import__(module_name)
                for obj_name in objects:
                    if obj_name in dir(module):
                        obj = getattr(module, obj_name)
                        self.assertIsNotNone(obj)
            except ImportError as e:
                self.fail(f"Failed to import {module_name}: {e}")


if __name__ == "__main__":
    unittest.main()
