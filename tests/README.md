# Tests Package

这个目录包含项目的单元测试和集成测试。

## 测试结构

```
tests/
├── __init__.py          # 包初始化
├── test_nfo_parser.py   # NFO 解析器测试
├── test_vsmeta_generator.py  # VSMETA 生成器测试
├── test_plugin_system.py # 插件系统测试
├── test_config.py       # 配置测试
└── conftest.py          # pytest 配置和 fixtures
```

## 运行测试

```bash
# 运行所有测试
pytest tests/

# 运行特定测试文件
pytest tests/test_plugin_system.py

# 运行特定测试函数
pytest tests/test_plugin_system.py::test_plugin_registration

# 显示详细输出
pytest tests/ -v

# 生成覆盖率报告
pytest tests/ --cov=nfo_to_vsmeta_converter_complete --cov-report=html
```

## 测试覆盖

- ✅ NFO 解析功能
- ✅ VSMETA 生成功能
- ✅ 插件系统
- ✅ 配置管理
- ✅ 文件扫描
- ✅ 断点续传

## 添加新测试

参考现有测试文件的格式创建新的测试用例。

确保：
1. 测试函数以 `test_` 开头
2. 使用描述性的函数名
3. 添加 docstring 说明测试目的
4. 使用 pytest fixtures 管理测试数据
5. 包含正向和负向测试用例
