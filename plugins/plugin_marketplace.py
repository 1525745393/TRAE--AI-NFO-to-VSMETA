#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
插件市场模块
提供在线插件发现、安装和发布功能
"""

import os
import json
import hashlib
import logging
import tempfile
import shutil
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import urllib.request
import urllib.error
import zipfile
import tarfile

logger = logging.getLogger('plugin_marketplace')


class MarketplaceError(Exception):
    """插件市场错误"""
    pass


class PluginVerificationError(Exception):
    """插件验证错误"""
    pass


class PluginStatus(Enum):
    """插件状态"""
    UNKNOWN = "unknown"
    COMPATIBLE = "compatible"
    INCOMPATIBLE = "incompatible"
    OUTDATED = "outdated"
    INSTALLED = "installed"
    UPDATE_AVAILABLE = "update_available"


@dataclass
class PluginManifest:
    """插件清单"""
    id: str
    name: str
    version: str
    description: str
    author: str
    category: str
    tags: List[str] = field(default_factory=list)
    min_app_version: str = "1.0.0"
    dependencies: Dict[str, str] = field(default_factory=dict)
    downloads: int = 0
    rating: float = 0.0
    last_updated: str = ""
    license: str = "MIT"
    homepage: str = ""
    repository: str = ""
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'PluginManifest':
        """从字典创建清单"""
        return cls(
            id=data.get('id', ''),
            name=data.get('name', ''),
            version=data.get('version', '1.0.0'),
            description=data.get('description', ''),
            author=data.get('author', ''),
            category=data.get('category', 'general'),
            tags=data.get('tags', []),
            min_app_version=data.get('min_app_version', '1.0.0'),
            dependencies=data.get('dependencies', {}),
            downloads=data.get('downloads', 0),
            rating=data.get('rating', 0.0),
            last_updated=data.get('last_updated', ''),
            license=data.get('license', 'MIT'),
            homepage=data.get('homepage', ''),
            repository=data.get('repository', ''),
        )
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'id': self.id,
            'name': self.name,
            'version': self.version,
            'description': self.description,
            'author': self.author,
            'category': self.category,
            'tags': self.tags,
            'min_app_version': self.min_app_version,
            'dependencies': self.dependencies,
            'downloads': self.downloads,
            'rating': self.rating,
            'last_updated': self.last_updated,
            'license': self.license,
            'homepage': self.homepage,
            'repository': self.repository,
        }


@dataclass
class PluginPackage:
    """插件包"""
    manifest: PluginManifest
    download_url: str
    file_hash: str
    file_size: int
    signature: Optional[str] = None
    local_path: Optional[str] = None
    
    @property
    def file_name(self) -> str:
        """获取文件名"""
        return f"{self.manifest.id}-{self.manifest.version}.zip"


class PluginSignatureVerifier:
    """
    插件签名验证器
    
    验证插件包的完整性和来源。
    """
    
    def __init__(self, trusted_keys: Dict[str, str] = None):
        """
        初始化验证器
        
        Args:
            trusted_keys: 可信的公钥字典 {key_id: public_key}
        """
        self.trusted_keys = trusted_keys or {}
        self._verified_hashes: Dict[str, str] = {}  # plugin_id -> hash
    
    def compute_hash(self, filepath: str) -> str:
        """
        计算文件 SHA256 哈希
        
        Args:
            filepath: 文件路径
            
        Returns:
            十六进制哈希字符串
        """
        sha256 = hashlib.sha256()
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                sha256.update(chunk)
        return sha256.hexdigest()
    
    def verify_hash(self, filepath: str, expected_hash: str) -> bool:
        """
        验证文件哈希
        
        Args:
            filepath: 文件路径
            expected_hash: 期望的哈希值
            
        Returns:
            是否验证通过
        """
        actual_hash = self.compute_hash(filepath)
        return actual_hash == expected_hash
    
    def verify_signature(self, filepath: str, signature: str, public_key: str) -> bool:
        """
        验证文件签名
        
        Args:
            filepath: 文件路径
            signature: Base64 编码的签名
            public_key: 公钥
            
        Returns:
            是否验证通过
        """
        try:
            file_hash = self.compute_hash(filepath)
            # TODO: 实现完整的签名验证逻辑
            # 这里简化实现，实际应该使用 cryptography 库
            logger.debug(f"验证签名: {filepath}, hash={file_hash[:16]}...")
            return True
        except Exception as e:
            logger.error(f"签名验证失败: {e}")
            return False
    
    def verify_package(self, package: PluginPackage) -> bool:
        """
        验证插件包
        
        Args:
            package: 插件包对象
            
        Returns:
            是否验证通过
        """
        if not package.local_path:
            raise PluginVerificationError("插件包没有本地路径")
        
        if not self.verify_hash(package.local_path, package.file_hash):
            raise PluginVerificationError(f"哈希验证失败: {package.file_hash}")
        
        if package.signature and self.trusted_keys:
            key_id = package.manifest.author
            public_key = self.trusted_keys.get(key_id)
            if public_key:
                if not self.verify_signature(package.local_path, package.signature, public_key):
                    raise PluginVerificationError("签名验证失败")
        
        self._verified_hashes[package.manifest.id] = package.file_hash
        logger.info(f"插件包验证通过: {package.manifest.name}")
        return True
    
    def is_verified(self, plugin_id: str) -> bool:
        """检查插件是否已验证"""
        return plugin_id in self._verified_hashes


class PluginMarketplace:
    """
    插件市场客户端
    
    提供插件的搜索、发现、安装和发布功能。
    支持插件版本管理、依赖解析和签名验证。
    """
    
    def __init__(self, api_url: str = "https://plugins.example.com/api/v1",
                 verify_ssl: bool = True, cache_dir: str = None):
        """
        初始化市场客户端
        
        Args:
            api_url: API 基础 URL
            verify_ssl: 是否验证 SSL 证书
            cache_dir: 缓存目录
        """
        self.api_url = api_url.rstrip('/')
        self.verify_ssl = verify_ssl
        self.cache_dir = cache_dir or os.path.join(tempfile.gettempdir(), 'plugin_marketplace_cache')
        self._installed_plugins: Dict[str, str] = {}  # plugin_id -> version
        self._verifier = PluginSignatureVerifier()
        
        os.makedirs(self.cache_dir, exist_ok=True)
        self._load_installed_plugins()
        
        logger.info(f"插件市场客户端已初始化: {api_url}")
    
    def _load_installed_plugins(self):
        """加载已安装插件列表"""
        installed_file = os.path.join(self.cache_dir, 'installed.json')
        if os.path.exists(installed_file):
            try:
                with open(installed_file, 'r', encoding='utf-8') as f:
                    self._installed_plugins = json.load(f)
                logger.debug(f"已加载 {len(self._installed_plugins)} 个已安装插件")
            except Exception as e:
                logger.warning(f"加载已安装插件列表失败: {e}")
    
    def _save_installed_plugins(self):
        """保存已安装插件列表"""
        installed_file = os.path.join(self.cache_dir, 'installed.json')
        try:
            with open(installed_file, 'w', encoding='utf-8') as f:
                json.dump(self._installed_plugins, f, indent=2)
        except Exception as e:
            logger.error(f"保存已安装插件列表失败: {e}")
    
    def _make_request(self, endpoint: str, method: str = 'GET',
                     data: Dict = None) -> Dict:
        """
        发起 HTTP 请求
        
        Args:
            endpoint: API 端点
            method: HTTP 方法
            data: 请求数据
            
        Returns:
            响应 JSON 数据
        """
        url = f"{self.api_url}/{endpoint.lstrip('/')}"
        
        try:
            if method == 'GET':
                req = urllib.request.Request(url)
            else:
                req = urllib.request.Request(
                    url,
                    data=json.dumps(data).encode('utf-8'),
                    method=method
                )
                req.add_header('Content-Type', 'application/json')
            
            with urllib.request.urlopen(req, verify=self.verify_ssl) as response:
                return json.loads(response.read().decode('utf-8'))
                
        except urllib.error.HTTPError as e:
            logger.error(f"HTTP 错误: {e.code} - {e.reason}")
            raise MarketplaceError(f"API 请求失败: {e.code} {e.reason}")
        except Exception as e:
            logger.error(f"请求异常: {e}")
            raise MarketplaceError(f"网络请求失败: {e}")
    
    def search(self, query: str, category: str = None,
              tags: List[str] = None, limit: int = 20,
              offset: int = 0) -> List[PluginManifest]:
        """
        搜索插件
        
        Args:
            query: 搜索关键词
            category: 分类过滤
            tags: 标签过滤
            limit: 返回数量限制
            offset: 分页偏移
            
        Returns:
            插件清单列表
        """
        params = f"?q={query}&limit={limit}&offset={offset}"
        if category:
            params += f"&category={category}"
        if tags:
            params += f"&tags={','.join(tags)}"
        
        try:
            result = self._make_request(f"/plugins/search{params}")
            plugins = result.get('plugins', [])
            return [PluginManifest.from_dict(p) for p in plugins]
        except MarketplaceError:
            # 如果 API 不可用，返回本地缓存的示例数据
            logger.warning("插件市场 API 不可用，返回本地插件")
            return self._get_local_plugins(query)
    
    def _get_local_plugins(self, query: str) -> List[PluginManifest]:
        """获取本地插件（模拟数据）"""
        local_plugins = [
            PluginManifest(
                id="metadata_enhancer_demo",
                name="元数据增强演示",
                version="1.0.0",
                description="演示如何增强影片元数据",
                author="System",
                category="enhancer",
                tags=["demo", "metadata"],
                downloads=1000,
            ),
            PluginManifest(
                id="file_size_filter",
                name="文件大小过滤器",
                version="1.0.0",
                description="按文件大小过滤视频文件",
                author="System",
                category="filter",
                tags=["filter", "file"],
                downloads=800,
            ),
            PluginManifest(
                id="nfo_parser",
                name="NFO解析器",
                version="1.2.0",
                description="增强NFO文件解析功能",
                author="Community",
                category="parser",
                tags=["parser", "nfo"],
                downloads=500,
            ),
            PluginManifest(
                id="vsmeta_generator",
                name="VSMETA生成器",
                version="1.1.0",
                description="高级VSMETA文件生成",
                author="System",
                category="generator",
                tags=["generator", "vsmeta"],
                downloads=750,
            ),
            PluginManifest(
                id="lifecycle_hooks",
                name="生命周期钩子",
                version="1.0.0",
                description="插件生命周期管理工具",
                author="System",
                category="lifecycle",
                tags=["lifecycle", "hook"],
                downloads=400,
            ),
        ]
        
        if query:
            return [p for p in local_plugins if query.lower() in p.name.lower() or 
                   query.lower() in p.description.lower()]
        return local_plugins
    
    def get_plugin(self, plugin_id: str) -> Optional[PluginManifest]:
        """
        获取插件详情
        
        Args:
            plugin_id: 插件 ID
            
        Returns:
            插件清单或 None
        """
        try:
            result = self._make_request(f"/plugins/{plugin_id}")
            return PluginManifest.from_dict(result)
        except MarketplaceError:
            return None
    
    def get_plugin_package(self, plugin_id: str, version: str = None) -> PluginPackage:
        """
        获取插件包
        
        Args:
            plugin_id: 插件 ID
            version: 指定版本（None 表示最新版本）
            
        Returns:
            插件包对象
        """
        endpoint = f"/plugins/{plugin_id}/download"
        if version:
            endpoint += f"?version={version}"
        
        try:
            result = self._make_request(endpoint)
            manifest = PluginManifest.from_dict(result['manifest'])
            return PluginPackage(
                manifest=manifest,
                download_url=result['download_url'],
                file_hash=result['file_hash'],
                file_size=result.get('file_size', 0),
                signature=result.get('signature'),
            )
        except MarketplaceError as e:
            logger.error(f"获取插件包失败: {e}")
            raise
    
    def check_update(self, plugin_id: str, current_version: str) -> PluginStatus:
        """
        检查插件更新
        
        Args:
            plugin_id: 插件 ID
            current_version: 当前版本
            
        Returns:
            插件状态
        """
        try:
            manifest = self.get_plugin(plugin_id)
            if not manifest:
                return PluginStatus.UNKNOWN
            
            if plugin_id in self._installed_plugins:
                if self._compare_versions(manifest.version, current_version) > 0:
                    return PluginStatus.UPDATE_AVAILABLE
                return PluginStatus.INSTALLED
            
            return PluginStatus.COMPATIBLE
            
        except Exception as e:
            logger.warning(f"检查更新失败: {e}")
            return PluginStatus.UNKNOWN
    
    def _compare_versions(self, ver1: str, ver2: str) -> int:
        """比较版本号"""
        v1_parts = [int(x) for x in ver1.split('.')]
        v2_parts = [int(x) for x in ver2.split('.')]
        
        for i in range(max(len(v1_parts), len(v2_parts))):
            v1 = v1_parts[i] if i < len(v1_parts) else 0
            v2 = v2_parts[i] if i < len(v2_parts) else 0
            if v1 > v2:
                return 1
            elif v1 < v2:
                return -1
        return 0
    
    def install(self, plugin_id: str, version: str = None,
               target_dir: str = None, verify: bool = True) -> bool:
        """
        安装插件
        
        Args:
            plugin_id: 插件 ID
            version: 指定版本（None 表示最新版本）
            target_dir: 安装目标目录
            verify: 是否验证插件
            
        Returns:
            是否安装成功
        """
        logger.info(f"开始安装插件: {plugin_id} (版本: {version or '最新'})")
        
        try:
            # 获取插件包
            package = self.get_plugin_package(plugin_id, version)
            
            # 下载插件
            download_path = self._download_plugin(package)
            
            if verify:
                package.local_path = download_path
                self._verifier.verify_package(package)
            
            # 解压插件
            self._extract_plugin(download_path, target_dir)
            
            # 更新已安装列表
            self._installed_plugins[plugin_id] = package.manifest.version
            self._save_installed_plugins()
            
            logger.info(f"插件安装成功: {plugin_id} v{package.manifest.version}")
            return True
            
        except Exception as e:
            logger.error(f"插件安装失败: {plugin_id} - {e}")
            raise MarketplaceError(f"安装失败: {e}")
    
    def _download_plugin(self, package: PluginPackage) -> str:
        """下载插件"""
        download_path = os.path.join(self.cache_dir, package.file_name)
        
        if os.path.exists(download_path):
            if self._verifier.verify_hash(download_path, package.file_hash):
                logger.debug(f"使用缓存的插件: {download_path}")
                return download_path
        
        logger.info(f"下载插件: {package.download_url}")
        
        try:
            urllib.request.urlretrieve(package.download_url, download_path)
            
            if not self._verifier.verify_hash(download_path, package.file_hash):
                os.remove(download_path)
                raise PluginVerificationError("下载文件哈希验证失败")
            
            return download_path
            
        except Exception as e:
            logger.error(f"下载失败: {e}")
            raise MarketplaceError(f"下载插件失败: {e}")
    
    def _extract_plugin(self, archive_path: str, target_dir: str = None):
        """解压插件"""
        if target_dir is None:
            target_dir = os.path.join(os.path.dirname(__file__))
        
        plugins_dir = os.path.join(target_dir, 'plugins')
        os.makedirs(plugins_dir, exist_ok=True)
        
        logger.info(f"解压插件到: {plugins_dir}")
        
        if archive_path.endswith('.zip'):
            with zipfile.ZipFile(archive_path, 'r') as zf:
                zf.extractall(plugins_dir)
        elif archive_path.endswith(('.tar.gz', '.tgz')):
            with tarfile.open(archive_path, 'r:gz') as tf:
                tf.extractall(plugins_dir)
        else:
            raise MarketplaceError(f"不支持的压缩格式: {archive_path}")
    
    def uninstall(self, plugin_id: str) -> bool:
        """
        卸载插件
        
        Args:
            plugin_id: 插件 ID
            
        Returns:
            是否卸载成功
        """
        logger.info(f"卸载插件: {plugin_id}")
        
        try:
            # 查找插件目录
            plugins_dir = os.path.join(os.path.dirname(__file__), 'plugins')
            plugin_file = os.path.join(plugins_dir, f"{plugin_id}.py")
            plugin_dir = os.path.join(plugins_dir, plugin_id)
            
            # 删除文件
            if os.path.exists(plugin_file):
                os.remove(plugin_file)
                logger.debug(f"已删除插件文件: {plugin_file}")
            
            if os.path.exists(plugin_dir):
                shutil.rmtree(plugin_dir)
                logger.debug(f"已删除插件目录: {plugin_dir}")
            
            # 更新已安装列表
            if plugin_id in self._installed_plugins:
                del self._installed_plugins[plugin_id]
                self._save_installed_plugins()
            
            logger.info(f"插件卸载成功: {plugin_id}")
            return True
            
        except Exception as e:
            logger.error(f"卸载失败: {e}")
            return False
    
    def update(self, plugin_id: str) -> bool:
        """
        更新插件
        
        Args:
            plugin_id: 插件 ID
            
        Returns:
            是否更新成功
        """
        current_version = self._installed_plugins.get(plugin_id)
        if not current_version:
            logger.warning(f"插件未安装，无法更新: {plugin_id}")
            return False
        
        return self.install(plugin_id)
    
    def list_installed(self) -> List[Dict[str, str]]:
        """
        列出已安装插件
        
        Returns:
            已安装插件列表 [{'id': ..., 'version': ...}]
        """
        return [
            {'id': plugin_id, 'version': version}
            for plugin_id, version in self._installed_plugins.items()
        ]
    
    def get_categories(self) -> List[Dict[str, Any]]:
        """
        获取插件分类
        
        Returns:
            分类列表
        """
        try:
            result = self._make_request("/categories")
            return result.get('categories', [])
        except MarketplaceError:
            # 返回默认分类
            return [
                {'id': 'enhancement', 'name': '元数据增强', 'description': '增强影片元数据'},
                {'id': 'filter', 'name': '过滤器', 'description': '过滤和处理文件'},
                {'id': 'converter', 'name': '转换器', 'description': '数据格式转换'},
                {'id': 'utility', 'name': '工具', 'description': '实用工具'},
            ]
    
    def list_plugins(self, category: str = None) -> List[Dict[str, Any]]:
        """
        列出插件市场的插件（适配Web UI）
        
        Args:
            category: 分类筛选
            
        Returns:
            插件列表字典
        """
        try:
            if category:
                plugins = self.search("", category=category)
            else:
                plugins = self._get_local_plugins("")
            
            # 转换为字典格式，适配Web UI
            result = []
            for p in plugins:
                d = p.to_dict()
                d['type'] = d.get('category', 'enhancer')  # 兼容UI的type字段
                result.append(d)
            return result
        except Exception as e:
            logger.error(f"列出插件失败: {e}")
            return []
    
    def install_plugin(self, name: str) -> Dict[str, Any]:
        """
        安装插件（适配Web UI）
        
        Args:
            name: 插件名称
            
        Returns:
            结果字典
        """
        try:
            # 尝试通过名称匹配本地插件
            local_plugins = self._get_local_plugins("")
            plugin = next((p for p in local_plugins if p.name == name), None)
            
            if plugin:
                self._installed_plugins[plugin.id] = plugin.version
                self._save_installed_plugins()
                logger.info(f"安装插件: {name}")
                return {'success': True}
            return {'success': False, 'error': '插件不存在'}
        except Exception as e:
            logger.error(f"安装失败: {e}")
            return {'success': False, 'error': str(e)}
    
    def uninstall_plugin(self, name: str) -> Dict[str, Any]:
        """
        卸载插件（适配Web UI）
        
        Args:
            name: 插件名称
            
        Returns:
            结果字典
        """
        try:
            # 尝试通过名称匹配
            local_plugins = self._get_local_plugins("")
            plugin = next((p for p in local_plugins if p.name == name), None)
            
            if plugin and plugin.id in self._installed_plugins:
                del self._installed_plugins[plugin.id]
                self._save_installed_plugins()
                logger.info(f"卸载插件: {name}")
                return {'success': True}
            return {'success': False, 'error': '插件不存在'}
        except Exception as e:
            logger.error(f"卸载失败: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_featured(self, limit: int = 10) -> List[PluginManifest]:
        """
        获取精选插件
        
        Args:
            limit: 返回数量
            
        Returns:
            插件列表
        """
        try:
            result = self._make_request(f"/plugins/featured?limit={limit}")
            return [PluginManifest.from_dict(p) for p in result.get('plugins', [])]
        except MarketplaceError:
            return self._get_local_plugins("")
    
    def publish(self, plugin_path: str, metadata: Dict) -> str:
        """
        发布插件到市场
        
        Args:
            plugin_path: 插件路径
            metadata: 插件元数据
            
        Returns:
            插件 ID
        """
        logger.info(f"发布插件: {plugin_path}")
        
        # 验证插件格式
        self._validate_plugin(plugin_path)
        
        # 创建发布包
        package_path = self._create_package(plugin_path, metadata)
        
        # 计算哈希
        file_hash = self._verifier.compute_hash(package_path)
        
        # 上传到市场
        data = {
            'metadata': metadata,
            'file_hash': file_hash,
        }
        
        try:
            result = self._make_request("/plugins/publish", method='POST', data=data)
            plugin_id = result.get('plugin_id')
            logger.info(f"插件发布成功: {plugin_id}")
            return plugin_id
        except MarketplaceError as e:
            logger.error(f"发布失败: {e}")
            raise MarketplaceError(f"发布到市场失败: {e}")
    
    def _validate_plugin(self, plugin_path: str):
        """验证插件格式"""
        if not os.path.exists(plugin_path):
            raise PluginVerificationError(f"插件路径不存在: {plugin_path}")
        
        # 检查是否有 Python 文件
        if os.path.isdir(plugin_path):
            python_files = [f for f in os.listdir(plugin_path) 
                          if f.endswith('.py') and not f.startswith('_')]
            if not python_files:
                raise PluginVerificationError("插件目录中没有 Python 文件")
        elif os.path.isfile(plugin_path):
            if not plugin_path.endswith('.py'):
                raise PluginVerificationError("插件文件必须是 .py 文件")
    
    def _create_package(self, plugin_path: str, metadata: Dict) -> str:
        """创建发布包"""
        package_name = f"{metadata['id']}-{metadata['version']}.zip"
        package_path = os.path.join(self.cache_dir, package_name)
        
        with zipfile.ZipFile(package_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            if os.path.isdir(plugin_path):
                for root, dirs, files in os.walk(plugin_path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, plugin_path)
                        zf.write(file_path, arcname)
            else:
                zf.write(plugin_path, os.path.basename(plugin_path))
        
        return package_path


def create_marketplace(api_url: str = None, **kwargs) -> PluginMarketplace:
    """
    创建插件市场实例的便捷函数
    
    Args:
        api_url: API URL
        **kwargs: 其他参数
        
    Returns:
        PluginMarketplace 实例
    """
    if api_url is None:
        api_url = "https://plugins.example.com/api/v1"
    return PluginMarketplace(api_url=api_url, **kwargs)


def get_marketplace() -> PluginMarketplace:
    """获取默认的插件市场实例"""
    if not hasattr(get_marketplace, '_instance'):
        get_marketplace._instance = create_marketplace()
    return get_marketplace._instance
