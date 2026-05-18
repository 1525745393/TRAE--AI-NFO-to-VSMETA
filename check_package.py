#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PyPI 包内容检查工具
详细检查包的结构和内容
"""

import os
import sys
import tarfile
import zipfile
from pathlib import Path


def print_banner():
    """打印横幅"""
    banner = """
╔═══════════════════════════════════════════════════════════════════╗
║                                                                   ║
║   📦 PyPI 包内容检查工具                                       ║
║   NFO to VSMETA Converter - v2.0.1                               ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
"""
    print(banner)


def check_tarball(tar_path):
    """检查 tar.gz 包"""
    print("\n" + "="*60)
    print("📦 检查源码包 (tar.gz)")
    print("="*60)
    
    if not os.path.exists(tar_path):
        print(f"❌ 文件不存在: {tar_path}")
        return None
    
    size = os.path.getsize(tar_path)
    print(f"✅ 文件: {tar_path}")
    print(f"   大小: {size / 1024:.2f} KB")
    
    try:
        with tarfile.open(tar_path, 'r:gz') as tar:
            members = tar.getmembers()
            print(f"   包含文件: {len(members)} 个")
            
            # 分类文件
            py_files = []
            md_files = []
            config_files = []
            other_files = []
            
            for member in members:
                if member.isfile():
                    path = member.name
                    if path.endswith('.py'):
                        py_files.append(path)
                    elif path.endswith('.md'):
                        md_files.append(path)
                    elif path.endswith(('.txt', '.toml', '.json', '.ini')):
                        config_files.append(path)
                    else:
                        other_files.append(path)
            
            print(f"\n📂 Python 文件: {len(py_files)} 个")
            for f in sorted(py_files)[:10]:
                print(f"   {f}")
            if len(py_files) > 10:
                print(f"   ... 还有 {len(py_files) - 10} 个文件")
            
            print(f"\n📄 Markdown 文件: {len(md_files)} 个")
            for f in sorted(md_files):
                print(f"   {f}")
            
            print(f"\n⚙️  配置文件: {len(config_files)} 个")
            for f in sorted(config_files):
                print(f"   {f}")
            
            print(f"\n📁 其他文件: {len(other_files)} 个")
            for f in sorted(other_files)[:5]:
                print(f"   {f}")
            if len(other_files) > 5:
                print(f"   ... 还有 {len(other_files) - 5} 个文件")
            
            # 检查关键文件
            print("\n🔍 检查关键文件:")
            key_files = [
                'nfo_to_vsmeta_converter_complete.py',
                'web_ui.py',
                'README.md',
                'LICENSE',
                'pyproject.toml'
            ]
            
            all_found = True
            for kf in key_files:
                found = any(kf in m.name for m in members)
                if found:
                    print(f"   ✅ {kf}")
                else:
                    print(f"   ❌ {kf} 未找到！")
                    all_found = False
            
            return {
                'total': len(members),
                'py': len(py_files),
                'md': len(md_files),
                'config': len(config_files),
                'other': len(other_files),
                'key_found': all_found
            }
    except Exception as e:
        print(f"❌ 读取失败: {e}")
        return None


def check_wheel(wheel_path):
    """检查 wheel 包"""
    print("\n" + "="*60)
    print("📦 检查 Wheel 包 (whl)")
    print("="*60)
    
    if not os.path.exists(wheel_path):
        print(f"❌ 文件不存在: {wheel_path}")
        return None
    
    size = os.path.getsize(wheel_path)
    print(f"✅ 文件: {wheel_path}")
    print(f"   大小: {size / 1024:.2f} KB")
    
    try:
        with zipfile.ZipFile(wheel_path, 'r') as zf:
            names = zf.namelist()
            print(f"   包含文件: {len(names)} 个")
            
            # 检查 metadata
            metadata_files = [n for n in names if 'METADATA' in n]
            if metadata_files:
                print("\n📋 元数据文件:")
                for mf in metadata_files:
                    print(f"   {mf}")
            
            # 检查 wheel 信息
            wheel_files = [n for n in names if n.endswith('.dist-info/WHEEL')]
            if wheel_files:
                print("\n📦 Wheel 信息:")
                content = zf.read(wheel_files[0]).decode('utf-8')
                print(content[:500])
            
            return {'total': len(names), 'metadata': len(metadata_files)}
    except Exception as e:
        print(f"❌ 读取失败: {e}")
        return None


def extract_and_check(tar_path):
    """解压并检查内容"""
    print("\n" + "="*60)
    print("🔍 解压检查源码包")
    print("="*60)
    
    extract_dir = Path('/tmp/nfo_package_check')
    extract_dir.mkdir(exist_ok=True)
    
    try:
        with tarfile.open(tar_path, 'r:gz') as tar:
            # 只解压前 20 个文件
            members = [m for m in tar.getmembers() if m.isfile()][:20]
            tar.extractall(extract_dir, members=members)
            
            print(f"✅ 解压到: {extract_dir}")
            print(f"   已解压 {len(members)} 个文件")
            
            # 检查 README
            readme_path = extract_dir / 'nfo_to_vsmeta-2.0.1' / 'README.md'
            if readme_path.exists():
                content = readme_path.read_text(encoding='utf-8')
                lines = content.split('\n')
                print("\n📄 README.md 预览 (前 20 行):")
                print("-" * 60)
                for line in lines[:20]:
                    print(line)
                if len(lines) > 20:
                    print(f"... 还有 {len(lines) - 20} 行")
            
            return True
    except Exception as e:
        print(f"❌ 解压失败: {e}")
        return False


def check_pip_install():
    """检查能否用 pip 安装"""
    print("\n" + "="*60)
    print("🔧 测试 pip 安装")
    print("="*60)
    
    import subprocess
    
    # 检查 pip 是否可用
    try:
        result = subprocess.run(
            [sys.executable, '-m', 'pip', '--version'],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            print(f"✅ pip 可用: {result.stdout.strip()}")
        else:
            print("❌ pip 不可用")
            return False
        
        # 尝试 dry-run 安装
        whl_path = Path('dist/nfo_to_vsmeta-2.0.1-py3-none-any.whl')
        if whl_path.exists():
            print("\n📦 测试安装 wheel 包...")
            result = subprocess.run(
                [sys.executable, '-m', 'pip', 'install', '--dry-run', '--force-reinstall', str(whl_path)],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                print("✅ 安装测试通过")
                # 检查是否有 entry points
                if 'nfo-to-vsmeta' in result.stdout or 'nfo-vsmeta-web' in result.stdout:
                    print("✅ 入口点 (entry points) 已配置")
                    print("   - nfo-to-vsmeta")
                    print("   - nfo-vsmeta-web")
            else:
                print("⚠️ 安装测试有问题:")
                print(result.stderr[:500])
            
            return result.returncode == 0
    except Exception as e:
        print(f"❌ pip 测试失败: {e}")
        return False


def print_summary(tar_info, wheel_info, install_ok):
    """打印总结"""
    print("\n" + "="*60)
    print("📊 检查总结")
    print("="*60)
    
    print("\n📦 源码包 (tar.gz):")
    if tar_info:
        print(f"   文件总数: {tar_info['total']}")
        print(f"   Python 文件: {tar_info['py']}")
        print(f"   Markdown 文件: {tar_info['md']}")
        print(f"   配置文件: {tar_info['config']}")
        print(f"   关键文件: {'✅ 全部找到' if tar_info['key_found'] else '❌ 部分缺失'}")
    
    print("\n📦 Wheel 包 (whl):")
    if wheel_info:
        print(f"   文件总数: {wheel_info['total']}")
        print(f"   元数据文件: {wheel_info['metadata']}")
    
    print(f"\n🔧 安装测试: {'✅ 通过' if install_ok else '⚠️ 需要检查'}")
    
    print("\n" + "="*60)
    print("🎯 结论")
    print("="*60)
    
    if tar_info and wheel_info and install_ok and tar_info['key_found']:
        print("✅ 包结构正确，可以上传到 PyPI！")
        print("\n下一步:")
        print("  python -m twine upload dist/*")
    else:
        print("⚠️ 包有问题，请检查上述错误")


def main():
    """主函数"""
    print_banner()
    
    tar_path = 'dist/nfo_to_vsmeta-2.0.1.tar.gz'
    wheel_path = 'dist/nfo_to_vsmeta-2.0.1-py3-none-any.whl'
    
    # 检查两个包
    tar_info = check_tarball(tar_path)
    wheel_info = check_wheel(wheel_path)
    
    # 解压检查
    if tar_info:
        extract_and_check(tar_path)
    
    # pip 安装测试
    install_ok = check_pip_install()
    
    # 打印总结
    print_summary(tar_info, wheel_info, install_ok)
    
    return 0


if __name__ == '__main__':
    os.chdir('/workspace')
    sys.exit(main())
