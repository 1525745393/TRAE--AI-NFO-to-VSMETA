#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NFO to VSMETA 转换器 - Web UI (完整功能版 v4.0)
================================================

基于 Flask 的 Web 管理界面，提供完整功能覆盖：
- 仪表盘：实时状态概览
- 配置管理：可视化编辑所有 36 个配置项
- 智能助手：自然语言配置输入
- 转换控制：启动/停止/查看进度 + 扫描结果预览
- 报告管理：HTML/CSV/TXT/智能分析/性能报告
- 断点管理：查看/重置/重试失败文件
- 备份管理：查看/清理备份文件
- 工具箱：NFO 验证、VSMETA 预览
- 插件管理：查看/加载/卸载插件
- 键盘快捷键支持

使用方法：
    python web_ui.py
    python web_ui.py --port 8080 --token mysecret

依赖：
    pip install flask

作者: AI Assistant
版本: 4.0.0
"""

import argparse
import glob
import hmac
import json
import logging
import os
import re
import secrets
import sys
import threading
import time
from dataclasses import asdict, is_dataclass
from datetime import datetime
from functools import wraps
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from flask import Flask, render_template_string, jsonify, request, send_file
    HAS_FLASK = True
except ImportError:
    HAS_FLASK = False

logger = logging.getLogger('web_ui')

_ALLOWED_LOG_LEVELS = {'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'}
_ALLOWED_PROCESS_MODES = {'thread', 'process'}
_ALLOWED_OUTPUT_FORMATS = {'vsmeta', 'nfo'}
_ALLOWED_REPORT_FORMATS = {'html', 'csv', 'txt'}

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)

_state_lock = threading.Lock()

_state: Dict[str, Any] = {
    'converter': None,
    'config': None,
    'is_running': False,
    'progress': {
        'total': 0, 'completed': 0, 'success': 0, 'failed': 0, 'skipped': 0,
        'current_file': '', 'start_time': None, 'end_time': None,
    },
    'scan_results': [],
    'selected_files': [],  # 批量选择的文件
    'logs': [],
    'max_logs': 1000,
    'csrf_token': secrets.token_hex(16),
    'api_token': '',
}

_PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))


def _validate_path(path: str, allow_absolute: bool = False) -> bool:
    if not path or not isinstance(path, str):
        return False
    if '..' in path:
        return False
    if not allow_absolute:
        real = os.path.realpath(os.path.join(_PROJECT_ROOT, path))
        return real.startswith(_PROJECT_ROOT)
    return True


def _validate_config_data(data: Optional[Dict]) -> Tuple[Optional[Dict], Optional[str]]:
    if data is None:
        return None, '请求体不能为空'
    if not isinstance(data, dict):
        return None, '请求体必须是 JSON 对象'

    validated = {}
    errors = []

    # 目录验证
    directory = data.get('directory')
    if directory is not None:
        if isinstance(directory, str):
            dirs = [d.strip() for d in directory.split(',') if d.strip()]
        elif isinstance(directory, list):
            dirs = [str(d).strip() for d in directory if str(d).strip()]
        else:
            errors.append('directory 格式无效'); dirs = []
        safe_dirs = []
        for d in dirs:
            if not _validate_path(d, allow_absolute=True):
                errors.append(f'目录路径不安全: {d}')
            else:
                safe_dirs.append(d)
        if safe_dirs:
            validated['directory'] = safe_dirs

    # 整数字段
    int_fields = {
        'max_workers': (1, 32, 4),
        'max_image_size_kb': (10, 10240, 200),
        'retry_attempts': (0, 20, 3),
        'min_size': (0, 107374182400, 0),
        'max_size': (0, 107374182400, 0),
        'log_file_max_size': (1024, 1073741824, 10485760),
        'log_file_backup_count': (0, 100, 5),
        'backup_max_count': (0, 1000, 5),
        'backup_max_age_days': (0, 3650, 30),
        'image_cache_max_size': (10, 500, 50),
        'checkpoint_save_interval': (1, 100, 10),
    }
    for field_name, (min_val, max_val, default) in int_fields.items():
        val = data.get(field_name)
        if val is not None:
            try:
                ival = int(val)
                if ival < min_val or ival > max_val:
                    errors.append(f'{field_name} 必须在 {min_val}-{max_val} 之间')
                else:
                    validated[field_name] = ival
            except (ValueError, TypeError):
                errors.append(f'{field_name} 必须是整数')

    # 浮点字段
    float_fields = {
        'image_compression_ratio': (0.1, 1.0, 0.8),
        'retry_delay': (0.1, 60.0, 1.0),
    }
    for field_name, (min_val, max_val, default) in float_fields.items():
        val = data.get(field_name)
        if val is not None:
            try:
                fval = float(val)
                if fval < min_val or fval > max_val:
                    errors.append(f'{field_name} 必须在 {min_val}-{max_val} 之间')
                else:
                    validated[field_name] = fval
            except (ValueError, TypeError):
                errors.append(f'{field_name} 必须是数字')

    # 枚举字段
    process_mode = data.get('process_mode')
    if process_mode is not None:
        if str(process_mode) not in _ALLOWED_PROCESS_MODES:
            errors.append(f'process_mode 必须是 {_ALLOWED_PROCESS_MODES} 之一')
        else:
            validated['process_mode'] = str(process_mode)

    log_level = data.get('log_level')
    if log_level is not None:
        if str(log_level).upper() not in _ALLOWED_LOG_LEVELS:
            errors.append(f'log_level 必须是 {_ALLOWED_LOG_LEVELS} 之一')
        else:
            validated['log_level'] = str(log_level).upper()

    # 列表字段
    def parse_list(val, allowed=None):
        if isinstance(val, str):
            items = [s.strip() for s in val.split(',') if s.strip()]
        elif isinstance(val, list):
            items = [str(s).strip() for s in val if str(s).strip()]
        else:
            return None, '格式无效'
        if allowed:
            invalid = set(items) - allowed
            if invalid:
                return None, f'包含不支持的值: {invalid}'
        return items, None

    for field_name in ['file_include_patterns', 'file_exclude_patterns']:
        val = data.get(field_name)
        if val is not None:
            items, err = parse_list(val)
            if err:
                errors.append(f'{field_name} {err}')
            elif items:
                validated[field_name] = items

    output_formats = data.get('output_formats')
    if output_formats is not None:
        items, err = parse_list(output_formats, _ALLOWED_OUTPUT_FORMATS)
        if err:
            errors.append(f'output_formats {err}')
        elif items:
            validated['output_formats'] = items

    for field_name in ['nfo_extensions', 'video_extensions']:
        val = data.get(field_name)
        if val is not None:
            items, err = parse_list(val)
            if err:
                errors.append(f'{field_name} {err}')
            elif items:
                validated[field_name] = items

    # 布尔字段
    for field_name in ['overwrite_existing', 'enable_backup', 'dry_run', 'delete_existing_vsmeta',
                       'tv_show_mode', 'auto_load_plugins', 'enable_ai_completion']:
        val = data.get(field_name)
        if val is not None:
            validated[field_name] = bool(val)

    # 字符串字段
    for field_name in ['file_regex', 'backup_dir', 'checkpoint_file', 'vsmeta_extension',
                       'plugin_dir', 'report_output_dir', 'log_file', 'ai_api_key', 'ai_api_url']:
        val = data.get(field_name)
        if val is not None:
            sval = str(val).strip()
            if sval and '..' in sval:
                errors.append(f'{field_name} 包含非法路径遍历字符')
            else:
                validated[field_name] = sval

    if errors:
        return validated, '; '.join(errors)
    return validated, None


def _check_api_token() -> bool:
    token = _state.get('api_token', '')
    if not token:
        return True
    auth = request.headers.get('X-API-Token', '') or request.args.get('token', '')
    return hmac.compare_digest(auth, token)


def _check_csrf() -> bool:
    token = request.headers.get('X-CSRF-Token', '') or request.form.get('csrf_token', '')
    expected = _state.get('csrf_token', '')
    if not expected:
        return True
    return hmac.compare_digest(token, expected)


def require_api_token(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not _check_api_token():
            return jsonify({'error': '未授权，请提供有效的 API Token'}), 401
        return f(*args, **kwargs)
    return decorated


def require_csrf(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not _check_csrf():
            return jsonify({'error': 'CSRF 验证失败'}), 403
        return f(*args, **kwargs)
    return decorated


def _add_log(level: str, message: str) -> None:
    safe_level = level if level in ('info', 'warning', 'error', 'success', 'debug') else 'info'
    entry = {'time': datetime.now().strftime('%H:%M:%S'), 'level': safe_level, 'message': str(message)}
    with _state_lock:
        _state['logs'].append(entry)
        if len(_state['logs']) > _state['max_logs']:
            _state['logs'] = _state['logs'][-_state['max_logs']:]
    log_level_map = {'debug': logging.DEBUG, 'info': logging.INFO, 'success': logging.INFO,
                     'warning': logging.WARNING, 'error': logging.ERROR}
    logger.log(log_level_map.get(safe_level, logging.INFO), message)


def _get_state(key: str, default: Any = None) -> Any:
    with _state_lock:
        return _state.get(key, default)


def _set_state(key: str, value: Any) -> None:
    with _state_lock:
        _state[key] = value


def _update_progress(updates: Dict) -> None:
    with _state_lock:
        _state['progress'].update(updates)


# ============================================================================
# 全局错误处理
# ============================================================================

@app.errorhandler(Exception)
def handle_exception(e: Exception) -> Tuple:
    logger.error(f'未捕获异常: {e}', exc_info=True)
    return jsonify({'error': '服务器内部错误', 'detail': str(e) if app.debug else '请查看服务器日志'}), 500


@app.errorhandler(400)
def handle_bad_request(e) -> Tuple:
    return jsonify({'error': '请求参数错误', 'detail': str(e)}), 400


@app.errorhandler(404)
def handle_not_found(e) -> Tuple:
    return jsonify({'error': '资源不存在'}), 404


@app.errorhandler(405)
def handle_method_not_allowed(e) -> Tuple:
    return jsonify({'error': '请求方法不允许'}), 405


# ============================================================================
# HTML 模板
# ============================================================================

INDEX_HTML = r'''<!DOCTYPE html>
<html lang="zh-CN" data-theme="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NFO to VSMETA 转换器</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&family=Noto+Sans+SC:wght@300;400;500;700&display=swap');
        :root,[data-theme="dark"]{--bg-primary:#0a0e17;--bg-secondary:#111827;--bg-card:#1a2236;--bg-input:#0f172a;--border:#1e3a5f;--border-active:#3b82f6;--text-primary:#e2e8f0;--text-secondary:#94a3b8;--text-muted:#64748b;--accent:#3b82f6;--accent-hover:#2563eb;--success:#22c55e;--warning:#f59e0b;--danger:#ef4444;--info:#06b6d4;--shadow:rgba(0,0,0,0.3);--toast-bg:#1e293b}
        [data-theme="light"]{--bg-primary:#f1f5f9;--bg-secondary:#fff;--bg-card:#fff;--bg-input:#f8fafc;--border:#e2e8f0;--border-active:#3b82f6;--text-primary:#1e293b;--text-secondary:#475569;--text-muted:#94a3b8;--accent:#3b82f6;--accent-hover:#2563eb;--success:#16a34a;--warning:#d97706;--danger:#dc2626;--info:#0891b2;--shadow:rgba(0,0,0,0.08);--toast-bg:#fff}
        *{margin:0;padding:0;box-sizing:border-box}
        body{font-family:'Noto+Sans+SC',sans-serif;background:var(--bg-primary);color:var(--text-primary);min-height:100vh;overflow-x:hidden;transition:background .3s,color .3s}
        body::before{content:'';position:fixed;inset:0;background-image:linear-gradient(rgba(59,130,246,.03) 1px,transparent 1px),linear-gradient(90deg,rgba(59,130,246,.03) 1px,transparent 1px);background-size:60px 60px;pointer-events:none;z-index:0}
        body::after{content:'';position:fixed;top:-200px;left:50%;transform:translateX(-50%);width:800px;height:400px;background:radial-gradient(ellipse,rgba(59,130,246,.08) 0%,transparent 70%);pointer-events:none;z-index:0}
        .app{position:relative;z-index:1}
        .navbar{display:flex;align-items:center;justify-content:space-between;padding:16px 32px;border-bottom:1px solid var(--border);backdrop-filter:blur(12px);background:rgba(10,14,23,.8);position:sticky;top:0;z-index:100;transition:background .3s}
        [data-theme="light"] .navbar{background:rgba(255,255,255,.85)}
        .navbar-brand{display:flex;align-items:center;gap:12px}
        .navbar-brand .logo{width:36px;height:36px;background:linear-gradient(135deg,var(--accent),#8b5cf6);border-radius:10px;display:flex;align-items:center;justify-content:center;font-size:18px;font-weight:700;color:#fff;font-family:'JetBrains Mono',monospace}
        .navbar-brand h1{font-size:18px;font-weight:600;letter-spacing:-.02em}
        .navbar-brand h1 span{color:var(--text-muted);font-weight:300;font-size:13px;margin-left:8px}
        .navbar-actions{display:flex;align-items:center;gap:12px}
        .navbar-status{display:flex;align-items:center;gap:8px;font-size:13px;color:var(--text-muted)}
        .status-dot{width:8px;height:8px;border-radius:50%;background:var(--success);animation:pulse 2s infinite}
        .status-dot.idle{background:var(--text-muted);animation:none}
        .status-dot.running{background:var(--accent)}
        @keyframes pulse{0%,100%{opacity:1}50%{opacity:.4}}
        .theme-toggle{background:none;border:1px solid var(--border);border-radius:8px;padding:6px 10px;cursor:pointer;font-size:16px;color:var(--text-secondary);transition:all .2s;line-height:1}
        .theme-toggle:hover{border-color:var(--border-active);color:var(--text-primary)}
        .kbd{font-family:'JetBrains Mono',monospace;font-size:11px;padding:2px 6px;background:var(--bg-input);border:1px solid var(--border);border-radius:4px;color:var(--text-muted)}
        .main{padding:32px;max-width:1400px;margin:0 auto}
        .tabs{display:flex;gap:4px;margin-bottom:24px;border-bottom:1px solid var(--border);padding-bottom:0;flex-wrap:wrap}
        .tab{padding:12px 16px;font-size:13px;font-weight:500;color:var(--text-muted);cursor:pointer;border-bottom:2px solid transparent;transition:all .2s;background:none;border-top:none;border-left:none;border-right:none;white-space:nowrap}
        .tab:hover{color:var(--text-secondary)}
        .tab.active{color:var(--accent);border-bottom-color:var(--accent)}
        .page{display:none}
        .page.active{display:block;animation:fadeIn .3s ease}
        @keyframes fadeIn{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:translateY(0)}}
        .stats-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:16px;margin-bottom:32px}
        .stat-card{background:var(--bg-card);border:1px solid var(--border);border-radius:12px;padding:20px;transition:border-color .2s,box-shadow .2s}
        .stat-card:hover{border-color:var(--border-active);box-shadow:0 4px 12px var(--shadow)}
        .stat-card .label{font-size:11px;color:var(--text-muted);text-transform:uppercase;letter-spacing:.05em;margin-bottom:6px}
        .stat-card .value{font-size:28px;font-weight:700;font-family:'JetBrains Mono',monospace;line-height:1}
        .stat-card .value.success{color:var(--success)}.stat-card .value.danger{color:var(--danger)}.stat-card .value.warning{color:var(--warning)}.stat-card .value.info{color:var(--info)}.stat-card .value.accent{color:var(--accent)}
        .card{background:var(--bg-card);border:1px solid var(--border);border-radius:12px;padding:24px;margin-bottom:24px;transition:background .3s,border-color .3s}
        .card-header{display:flex;align-items:center;justify-content:space-between;margin-bottom:20px;flex-wrap:wrap;gap:8px}
        .card-header h2{font-size:16px;font-weight:600}
        .progress-bar-container{background:var(--bg-input);border-radius:8px;height:24px;overflow:hidden;position:relative}
        .progress-bar-fill{height:100%;background:linear-gradient(90deg,var(--accent),#8b5cf6);border-radius:8px;transition:width .5s ease;position:relative}
        .progress-bar-fill::after{content:'';position:absolute;inset:0;background:linear-gradient(90deg,transparent,rgba(255,255,255,.1),transparent);animation:shimmer 2s infinite}
        @keyframes shimmer{0%{transform:translateX(-100%)}100%{transform:translateX(100%)}}
        .progress-bar-text{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:600;font-family:'JetBrains Mono',monospace;color:#fff;text-shadow:0 1px 2px rgba(0,0,0,.5)}
        .table-wrapper{overflow-x:auto}
        table{width:100%;border-collapse:collapse;font-size:13px}
        th{text-align:left;padding:10px 14px;font-weight:500;color:var(--text-muted);font-size:11px;text-transform:uppercase;letter-spacing:.05em;border-bottom:1px solid var(--border)}
        td{padding:8px 14px;border-bottom:1px solid rgba(30,58,95,.15);color:var(--text-secondary)}
        [data-theme="light"] td{border-bottom-color:rgba(0,0,0,.06)}
        tr:hover td{background:rgba(59,130,246,.03)}
        .badge{display:inline-block;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:600}
        .badge.success{background:rgba(34,197,94,.15);color:var(--success)}.badge.danger{background:rgba(239,68,68,.15);color:var(--danger)}.badge.warning{background:rgba(245,158,11,.15);color:var(--warning)}.badge.info{background:rgba(6,182,212,.15);color:var(--info)}
        .btn{padding:8px 16px;border:1px solid var(--border);border-radius:8px;background:var(--bg-card);color:var(--text-primary);font-size:13px;font-weight:500;cursor:pointer;transition:all .2s;font-family:inherit}
        .btn:hover{border-color:var(--border-active);background:rgba(59,130,246,.1)}
        .btn-primary{background:var(--accent);border-color:var(--accent);color:#fff}.btn-primary:hover{background:var(--accent-hover)}
        .btn-danger{background:rgba(239,68,68,.15);border-color:var(--danger);color:var(--danger)}.btn-danger:hover{background:rgba(239,68,68,.25)}
        .btn-success{background:rgba(34,197,94,.15);border-color:var(--success);color:var(--success)}.btn-success:hover{background:rgba(34,197,94,.25)}
        .btn-sm{padding:4px 12px;font-size:11px}
        .btn-group{display:flex;gap:8px;flex-wrap:wrap}
        .form-group{margin-bottom:14px}
        .form-group label{display:block;font-size:12px;color:var(--text-muted);margin-bottom:5px;font-weight:500}
        .form-control{width:100%;padding:9px 12px;background:var(--bg-input);border:1px solid var(--border);border-radius:8px;color:var(--text-primary);font-size:13px;font-family:'JetBrains Mono',monospace;transition:border-color .2s,background .3s}
        .form-control:focus{outline:none;border-color:var(--accent)}
        .form-row{display:grid;grid-template-columns:1fr 1fr;gap:14px}
        .form-row-3{display:grid;grid-template-columns:1fr 1fr 1fr;gap:14px}
        .form-row-4{display:grid;grid-template-columns:repeat(4,1fr);gap:14px}
        .section-title{font-size:13px;font-weight:600;color:var(--accent);margin:20px 0 12px;padding-bottom:8px;border-bottom:1px solid var(--border);display:flex;align-items:center;gap:8px}
        .section-title:first-child{margin-top:0}
        .log-container{background:var(--bg-input);border:1px solid var(--border);border-radius:8px;padding:16px;max-height:500px;overflow-y:auto;font-family:'JetBrains Mono',monospace;font-size:12px;line-height:1.8}
        .log-entry{color:var(--text-secondary)}.log-entry .time{color:var(--text-muted)}.log-entry .level-info{color:var(--info)}.log-entry .level-warning{color:var(--warning)}.log-entry .level-error{color:var(--danger)}.log-entry .level-success{color:var(--success)}.log-entry .level-debug{color:var(--text-muted)}
        .empty-state{text-align:center;padding:40px 20px;color:var(--text-muted)}.empty-state .icon{font-size:40px;margin-bottom:12px}.empty-state p{font-size:14px}
        .toast-container{position:fixed;top:80px;right:24px;z-index:9999;display:flex;flex-direction:column;gap:8px;pointer-events:none}
        .toast{background:var(--toast-bg);border:1px solid var(--border);border-radius:10px;padding:12px 20px;font-size:13px;color:var(--text-primary);box-shadow:0 8px 24px var(--shadow);animation:toastIn .3s ease,toastOut .3s ease 2.7s forwards;pointer-events:auto;max-width:360px;backdrop-filter:blur(12px);display:flex;align-items:center;gap:10px}
        .toast.toast-success{border-left:3px solid var(--success)}.toast.toast-error{border-left:3px solid var(--danger)}.toast.toast-warning{border-left:3px solid var(--warning)}.toast.toast-info{border-left:3px solid var(--info)}
        .toast-icon{font-size:16px;flex-shrink:0}
        @keyframes toastIn{from{opacity:0;transform:translateX(40px)}to{opacity:1;transform:translateX(0)}}
        @keyframes toastOut{from{opacity:1;transform:translateX(0)}to{opacity:0;transform:translateX(40px)}}
        .modal-overlay{position:fixed;inset:0;background:rgba(0,0,0,.5);backdrop-filter:blur(4px);z-index:10000;display:flex;align-items:center;justify-content:center;animation:fadeIn .2s ease}
        .modal-box{background:var(--bg-card);border:1px solid var(--border);border-radius:16px;padding:32px;max-width:420px;width:90%;box-shadow:0 16px 48px var(--shadow)}
        .modal-box h3{font-size:16px;margin-bottom:12px}.modal-box p{font-size:14px;color:var(--text-secondary);margin-bottom:24px;line-height:1.6}
        .modal-actions{display:flex;gap:8px;justify-content:flex-end}
        .checkbox-group{display:flex;flex-wrap:wrap;gap:12px 20px}
        .checkbox-group label{display:flex;align-items:center;gap:6px;font-size:12px;color:var(--text-secondary);cursor:pointer}
        .checkbox-group input[type="checkbox"]{accent-color:var(--accent)}
        .smart-input{background:linear-gradient(90deg,var(--bg-input),rgba(59,130,246,.05));border:1px solid var(--border);border-radius:8px;padding:12px;display:flex;gap:8px;align-items:center}
        .smart-input input{flex:1;background:transparent;border:none;color:var(--text-primary);font-size:14px;outline:none;font-family:inherit}
        .smart-input input::placeholder{color:var(--text-muted)}
        .smart-input button{padding:6px 12px;font-size:12px}
        .file-select{width:18px;height:18px;accent-color:var(--accent);cursor:pointer}
        .help-text{font-size:11px;color:var(--text-muted);margin-top:4px}
        ::-webkit-scrollbar{width:6px;height:6px}::-webkit-scrollbar-track{background:transparent}::-webkit-scrollbar-thumb{background:var(--border);border-radius:3px}::-webkit-scrollbar-thumb:hover{background:var(--border-active)}
        @media(max-width:768px){.main{padding:16px}.stats-grid{grid-template-columns:repeat(2,1fr)}.form-row,.form-row-3,.form-row-4{grid-template-columns:1fr}.navbar{padding:12px 16px}.navbar-brand h1 span{display:none}.tabs{gap:2px}.tab{padding:10px 12px;font-size:12px}}
        .shortcut-hint{position:fixed;bottom:16px;right:16px;background:var(--bg-card);border:1px solid var(--border);border-radius:8px;padding:12px 16px;font-size:12px;color:var(--text-muted);z-index:100;opacity:0;transition:opacity .3s}
        .shortcut-hint.visible{opacity:1}
    </style>
</head>
<body>
    <div class="app">
        <div class="toast-container" id="toastContainer"></div>
        <div id="modalContainer"></div>
        <nav class="navbar">
            <div class="navbar-brand">
                <div class="logo">N</div>
                <h1>NFO→VSMETA<span>Web 控制台 v4.0</span></h1>
            </div>
            <div class="navbar-actions">
                <div class="navbar-status"><div class="status-dot" id="statusDot"></div><span id="statusText">就绪</span></div>
                <button class="theme-toggle" id="themeToggle" onclick="toggleTheme()" title="切换主题 (T)">🌙</button>
            </div>
        </nav>
        <div class="main">
            <div class="tabs">
                <button class="tab active" data-tab="dashboard" onclick="switchTab('dashboard')">📊 仪表盘</button>
                <button class="tab" data-tab="config" onclick="switchTab('config')">⚙️ 配置</button>
                <button class="tab" data-tab="smart" onclick="switchTab('smart')">🤖 智能助手</button>
                <button class="tab" data-tab="convert" onclick="switchTab('convert')">🚀 转换</button>
                <button class="tab" data-tab="tools" onclick="switchTab('tools')">🧰 工具箱</button>
                <button class="tab" data-tab="report" onclick="switchTab('report')">📄 报告</button>
                <button class="tab" data-tab="checkpoint" onclick="switchTab('checkpoint')">💾 断点</button>
                <button class="tab" data-tab="backup" onclick="switchTab('backup')">📦 备份</button>
                <button class="tab" data-tab="logs" onclick="switchTab('logs')">📋 日志</button>
                <button class="tab" data-tab="plugins" onclick="switchTab('plugins')">🔌 插件</button>
            </div>

            <!-- ========== 仪表盘 ========== -->
            <div class="page active" id="page-dashboard">
                <div class="stats-grid">
                    <div class="stat-card"><div class="label">总文件数</div><div class="value accent" id="statTotal">0</div></div>
                    <div class="stat-card"><div class="label">已处理</div><div class="value info" id="statProcessed">0</div></div>
                    <div class="stat-card"><div class="label">成功</div><div class="value success" id="statSuccess">0</div></div>
                    <div class="stat-card"><div class="label">失败</div><div class="value danger" id="statFailed">0</div></div>
                    <div class="stat-card"><div class="label">跳过</div><div class="value warning" id="statSkipped">0</div></div>
                    <div class="stat-card"><div class="label">成功率</div><div class="value" id="statRate">0%</div></div>
                </div>
                <div class="card">
                    <div class="card-header"><h2>转换进度</h2><span id="progressPercent" style="font-family:'JetBrains Mono',monospace;font-size:14px;color:var(--accent)">0%</span></div>
                    <div class="progress-bar-container"><div class="progress-bar-fill" id="progressBar" style="width:0%"></div><div class="progress-bar-text" id="progressText">等待开始...</div></div>
                    <div style="margin-top:12px;font-size:12px;color:var(--text-muted)" id="progressDetail"></div>
                </div>
                <div class="card">
                    <div class="card-header"><h2>最近处理</h2></div>
                    <div class="table-wrapper">
                        <table><thead><tr><th>文件</th><th>目录</th><th>结果</th><th>详情</th><th>时间</th></tr></thead>
                        <tbody id="recentFiles"><tr><td colspan="5" class="empty-state"><p>暂无处理记录</p></td></tr></tbody></table>
                    </div>
                </div>
                <div class="card">
                    <div class="card-header"><h2>快捷键</h2></div>
                    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px;font-size:13px;color:var(--text-secondary)">
                        <div><span class="kbd">Ctrl+S</span> 保存配置</div>
                        <div><span class="kbd">Ctrl+R</span> 刷新状态</div>
                        <div><span class="kbd">Ctrl+Enter</span> 开始转换</div>
                        <div><span class="kbd">ESC</span> 关闭弹窗</div>
                        <div><span class="kbd">1-9</span> 切换标签页</div>
                        <div><span class="kbd">T</span> 切换主题</div>
                    </div>
                </div>
            </div>

            <!-- ========== 配置 ========== -->
            <div class="page" id="page-config">
                <div class="card">
                    <div class="card-header"><h2>基本配置</h2><div class="btn-group"><button class="btn" onclick="loadConfig()">📂 加载</button><button class="btn" onclick="resetConfig()">🔄 重置</button><button class="btn" onclick="exportConfig()">📤 导出</button><button class="btn" onclick="importConfig()">📥 导入</button><button class="btn btn-primary" onclick="saveConfig()">💾 保存 <span class="kbd">Ctrl+S</span></button></div></div>
                    <div class="form-group"><label>处理目录（多个用逗号分隔）</label><input type="text" class="form-control" id="cfgDirectory" value="." placeholder="/path/to/movies"></div>
                    <div class="form-row">
                        <div class="form-group"><label>线程数 (1-32)</label><input type="number" class="form-control" id="cfgWorkers" value="4" min="1" max="32"></div>
                        <div class="form-group"><label>处理模式</label><select class="form-control" id="cfgMode"><option value="thread">多线程</option><option value="process">多进程</option></select></div>
                    </div>
                    <div class="form-row">
                        <div class="form-group"><label>图片最大大小 KB (10-10240)</label><input type="number" class="form-control" id="cfgMaxImgSize" value="200"></div>
                        <div class="form-group"><label>图片压缩比例 (0.1-1.0)</label><input type="number" class="form-control" id="cfgCompression" value="0.8" min="0.1" max="1.0" step="0.1"></div>
                    </div>
                    <div class="form-row">
                        <div class="form-group"><label>重试次数 (0-20)</label><input type="number" class="form-control" id="cfgRetries" value="3" min="0" max="20"></div>
                        <div class="form-group"><label>重试延迟 秒 (0.1-60)</label><input type="number" class="form-control" id="cfgRetryDelay" value="1.0" min="0.1" max="60" step="0.1"></div>
                    </div>
                </div>

                <div class="card">
                    <div class="card-header"><h2>文件过滤</h2></div>
                    <div class="form-row">
                        <div class="form-group"><label>包含模式（通配符，逗号分隔）</label><input type="text" class="form-control" id="cfgInclude" placeholder="*.mkv, *.mp4"></div>
                        <div class="form-group"><label>排除模式（通配符，逗号分隔）</label><input type="text" class="form-control" id="cfgExclude" placeholder="*.sample*, *.txt"></div>
                    </div>
                    <div class="form-row">
                        <div class="form-group"><label>文件名正则过滤</label><input type="text" class="form-control" id="cfgRegex" placeholder=".*1080p.*"></div>
                        <div class="form-group"><label>输出格式（vsmeta, nfo）</label><input type="text" class="form-control" id="cfgFormats" value="vsmeta" placeholder="vsmeta, nfo"></div>
                    </div>
                    <div class="form-row">
                        <div class="form-group"><label>最小文件大小（字节，0=不限）</label><input type="number" class="form-control" id="cfgMinSize" value="0" min="0"></div>
                        <div class="form-group"><label>最大文件大小（字节，0=不限）</label><input type="number" class="form-control" id="cfgMaxSize" value="0" min="0"></div>
                    </div>
                    <div class="form-row">
                        <div class="form-group"><label>NFO 扩展名（逗号分隔）</label><input type="text" class="form-control" id="cfgNfoExt" value=".nfo" placeholder=".nfo, .NFO"></div>
                        <div class="form-group"><label>视频扩展名（逗号分隔）</label><input type="text" class="form-control" id="cfgVideoExt" value=".mp4, .mkv, .avi, .ts, .wmv, .rmvb, .mov, .m4v" placeholder=".mp4, .mkv"></div>
                    </div>
                </div>

                <div class="card">
                    <div class="card-header"><h2>路径与输出</h2></div>
                    <div class="form-row">
                        <div class="form-group"><label>VSMETA 扩展名</label><input type="text" class="form-control" id="cfgVsmetaExt" value=".vsmeta"></div>
                        <div class="form-group"><label>备份目录名</label><input type="text" class="form-control" id="cfgBackupDir" value=".backup"></div>
                    </div>
                    <div class="form-row">
                        <div class="form-group"><label>断点文件名</label><input type="text" class="form-control" id="cfgCheckpointFile" value="conversion_checkpoint.json"></div>
                        <div class="form-group"><label>报告输出目录</label><input type="text" class="form-control" id="cfgReportDir" placeholder="reports/"></div>
                    </div>
                </div>

                <div class="card">
                    <div class="card-header"><h2>性能优化</h2></div>
                    <div class="form-row">
                        <div class="form-group"><label>图片缓存大小 (10-500)</label><input type="number" class="form-control" id="cfgImgCacheSize" value="50" min="10" max="500"><div class="help-text">缓存压缩后的图片，减少重复处理</div></div>
                        <div class="form-group"><label>断点保存间隔 (1-100)</label><input type="number" class="form-control" id="cfgCheckpointInterval" value="10" min="1" max="100"><div class="help-text">每处理多少个文件后保存断点</div></div>
                    </div>
                </div>

                <div class="card">
                    <div class="card-header"><h2>日志配置</h2></div>
                    <div class="form-row">
                        <div class="form-group"><label>日志级别</label><select class="form-control" id="cfgLogLevel"><option value="DEBUG">DEBUG</option><option value="INFO" selected>INFO</option><option value="WARNING">WARNING</option><option value="ERROR">ERROR</option></select></div>
                        <div class="form-group"><label>日志文件路径</label><input type="text" class="form-control" id="cfgLogFile" placeholder="converter.log"></div>
                    </div>
                    <div class="form-row">
                        <div class="form-group"><label>日志文件最大大小（字节）</label><input type="number" class="form-control" id="cfgLogFileMaxSize" value="10485760" min="1024"></div>
                        <div class="form-group"><label>日志文件备份数量</label><input type="number" class="form-control" id="cfgLogFileBackupCount" value="5" min="0" max="100"></div>
                    </div>
                </div>

                <div class="card">
                    <div class="card-header"><h2>备份策略</h2></div>
                    <div class="form-row">
                        <div class="form-group"><label>每个文件最大备份数</label><input type="number" class="form-control" id="cfgBackupMaxCount" value="5" min="0"></div>
                        <div class="form-group"><label>备份最大保留天数</label><input type="number" class="form-control" id="cfgBackupMaxAge" value="30" min="0"></div>
                    </div>
                </div>

                <div class="card">
                    <div class="card-header"><h2>开关选项</h2></div>
                    <div class="checkbox-group">
                        <label><input type="checkbox" id="cfgOverwrite"> 覆盖已有文件</label>
                        <label><input type="checkbox" id="cfgBackup" checked> 启用备份</label>
                        <label><input type="checkbox" id="cfgDeleteVsmeta"> 删除已有 VSMETA</label>
                        <label><input type="checkbox" id="cfgDryRun"> 预演模式</label>
                        <label><input type="checkbox" id="cfgTvShow"> 剧集模式</label>
                        <label><input type="checkbox" id="cfgAutoLoadPlugins"> 自动加载插件</label>
                    </div>
                </div>

                <div class="card">
                    <div class="card-header"><h2>插件配置</h2></div>
                    <div class="form-group"><label>插件目录</label><input type="text" class="form-control" id="cfgPluginDir" value="plugins" placeholder="plugins/"></div>
                </div>

                <div class="card">
                    <div class="card-header"><h2>AI 补全（预留）</h2></div>
                    <div class="form-group"><label style="display:flex;align-items:center;gap:8px"><input type="checkbox" id="cfgAiEnable"> 启用 AI 补全</label></div>
                    <div class="form-row">
                        <div class="form-group"><label>AI API 密钥</label><input type="password" class="form-control" id="cfgAiKey" placeholder="sk-..."></div>
                        <div class="form-group"><label>AI API 地址</label><input type="text" class="form-control" id="cfgAiUrl" placeholder="https://api.openai.com/v1"></div>
                    </div>
                </div>
            </div>

            <!-- ========== 智能助手 ========== -->
            <div class="page" id="page-smart">
                <div class="card">
                    <div class="card-header"><h2>🤖 智能助手</h2></div>
                    <p style="font-size:14px;color:var(--text-secondary);margin-bottom:16px">用自然语言描述你的需求，智能助手会自动配置参数。</p>
                    <div class="smart-input">
                        <input type="text" id="smartCommand" placeholder="例如：只处理2020年以后的mp4文件，线程数8，启用备份" onkeydown="if(event.key==='Enter')executeSmartCommand()">
                        <button class="btn btn-primary" onclick="executeSmartCommand()">执行</button>
                    </div>
                    <div id="smartResult" style="margin-top:16px"></div>
                </div>
                <div class="card">
                    <div class="card-header"><h2>示例命令</h2></div>
                    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:12px">
                        <div class="stat-card" style="cursor:pointer" onclick="setSmartCommand('只处理mp4和mkv文件，图片压缩到80%质量')">
                            <div class="label">视频过滤</div>
                            <div style="font-size:13px;color:var(--text-secondary)">只处理mp4和mkv文件，图片压缩到80%质量</div>
                        </div>
                        <div class="stat-card" style="cursor:pointer" onclick="setSmartCommand('处理大于1GB的文件，使用4个线程，不备份')">
                            <div class="label">大小过滤</div>
                            <div style="font-size:13px;color:var(--text-secondary)">处理大于1GB的文件，使用4个线程，不备份</div>
                        </div>
                        <div class="stat-card" style="cursor:pointer" onclick="setSmartCommand('启用剧集模式，只处理包含S01E01的文件')">
                            <div class="label">剧集模式</div>
                            <div style="font-size:13px;color:var(--text-secondary)">启用剧集模式，只处理包含S01E01的文件</div>
                        </div>
                        <div class="stat-card" style="cursor:pointer" onclick="setSmartCommand('预演模式，测试配置但不实际写入')">
                            <div class="label">预演测试</div>
                            <div style="font-size:13px;color:var(--text-secondary)">预演模式，测试配置但不实际写入</div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- ========== 转换 ========== -->
            <div class="page" id="page-convert">
                <div class="card">
                    <div class="card-header"><h2>转换控制</h2><div class="btn-group"><button class="btn btn-success" id="btnStart" onclick="startConversion()">▶️ 开始转换 <span class="kbd">Ctrl+Enter</span></button><button class="btn btn-danger" id="btnStop" onclick="confirmStopConversion()" style="display:none">⏹️ 停止</button><button class="btn" onclick="startConversion(true)">▶️ 仅转换选中</button></div></div>
                    <div id="convertStatus" class="empty-state"><div class="icon">🎬</div><p>配置好参数后，点击"开始转换"</p></div>
                </div>
                <div class="card">
                    <div class="card-header"><h2>扫描结果 <span id="scanCount" style="font-size:12px;color:var(--text-muted)"></span></h2><div class="btn-group"><button class="btn btn-sm" onclick="selectAllFiles()">全选</button><button class="btn btn-sm" onclick="deselectAllFiles()">取消全选</button></div></div>
                    <div class="table-wrapper">
                        <table><thead><tr><th><input type="checkbox" class="file-select" onchange="toggleSelectAll(this)"></th><th>#</th><th>文件名</th><th>目录</th><th>大小</th><th>NFO</th><th>状态</th></tr></thead>
                        <tbody id="scanResults"><tr><td colspan="7" class="empty-state"><p>点击"开始转换"后显示扫描结果</p></td></tr></tbody></table>
                    </div>
                </div>
            </div>

            <!-- ========== 工具箱 ========== -->
            <div class="page" id="page-tools">
                <div class="card">
                    <div class="card-header"><h2>🧰 NFO 验证</h2></div>
                    <p style="font-size:14px;color:var(--text-secondary);margin-bottom:16px">验证 NFO 文件格式是否正确、字段是否完整。</p>
                    <div class="form-group"><label>NFO 文件路径</label><div style="display:flex;gap:8px"><input type="text" class="form-control" id="nfoPath" placeholder="/path/to/movie.nfo"><button class="btn btn-primary" onclick="validateNfo()">🔍 验证</button></div></div>
                    <div id="nfoValidationResult"></div>
                </div>
                <div class="card">
                    <div class="card-header"><h2>📄 VSMETA 预览</h2></div>
                    <p style="font-size:14px;color:var(--text-secondary);margin-bottom:16px">解析并预览已有的 VSMETA 文件内容。</p>
                    <div class="form-group"><label>VSMETA 文件路径</label><div style="display:flex;gap:8px"><input type="text" class="form-control" id="vsmetaPath" placeholder="/path/to/movie.vsmeta"><button class="btn btn-primary" onclick="previewVsmeta()">👁️ 预览</button></div></div>
                    <div id="vsmetaPreviewResult"></div>
                </div>
            </div>

            <!-- ========== 报告 ========== -->
            <div class="page" id="page-report">
                <div class="card">
                    <div class="card-header"><h2>转换报告</h2><div class="btn-group"><button class="btn btn-primary" onclick="generateReport('html')">📄 HTML</button><button class="btn" onclick="generateReport('csv')">📊 CSV</button><button class="btn" onclick="generateReport('txt')">📝 TXT</button></div></div>
                    <div id="reportContent" class="empty-state"><div class="icon">📄</div><p>转换完成后可生成报告</p></div>
                </div>
                <div class="card">
                    <div class="card-header"><h2>高级报告</h2><div class="btn-group"><button class="btn" onclick="generateAdvancedReport('smart-analysis','html')">🧠 智能分析 (HTML)</button><button class="btn" onclick="generateAdvancedReport('smart-analysis','txt')">🧠 智能分析 (TXT)</button><button class="btn" onclick="generateAdvancedReport('performance','html')">⚡ 性能报告 (HTML)</button><button class="btn" onclick="generateAdvancedReport('performance','txt')">⚡ 性能报告 (TXT)</button></div></div>
                    <div id="advancedReportContent" class="empty-state"><div class="icon">📊</div><p>转换完成后可生成高级分析报告</p></div>
                </div>
            </div>

            <!-- ========== 断点 ========== -->
            <div class="page" id="page-checkpoint">
                <div class="card">
                    <div class="card-header"><h2>断点续传</h2><div class="btn-group"><button class="btn" onclick="refreshCheckpoint()">🔄 刷新</button><button class="btn btn-danger" onclick="confirmResetCheckpoint()">🗑️ 重置断点</button></div></div>
                    <div id="checkpointInfo"></div>
                </div>
                <div class="card">
                    <div class="card-header"><h2>重试失败文件</h2></div>
                    <p style="font-size:13px;color:var(--text-secondary);margin-bottom:16px">清除失败文件的断点记录，使其在下次转换时被重新处理。</p>
                    <div class="btn-group"><button class="btn btn-primary" onclick="retryFailed('all')">🔄 全部重试</button><button class="btn" onclick="retryFailed('nfo_missing')">📄 仅 NFO 缺失</button><button class="btn" onclick="retryFailed('error')">⚠️ 仅转换错误</button><button class="btn" onclick="retryFailed('delete_failed')">🗑️ 仅删除失败</button></div>
                </div>
            </div>

            <!-- ========== 备份 ========== -->
            <div class="page" id="page-backup">
                <div class="card">
                    <div class="card-header"><h2>备份管理</h2><div class="btn-group"><button class="btn" onclick="refreshBackups()">🔄 刷新</button><button class="btn btn-danger" onclick="confirmCleanBackups()">🧹 清理过期备份</button></div></div>
                    <div class="table-wrapper">
                        <table><thead><tr><th>文件名</th><th>大小</th><th>修改时间</th><th>操作</th></tr></thead>
                        <tbody id="backupList"><tr><td colspan="4" class="empty-state"><p>暂无备份文件</p></td></tr></tbody></table>
                    </div>
                </div>
            </div>

            <!-- ========== 日志 ========== -->
            <div class="page" id="page-logs">
                <div class="card">
                    <div class="card-header"><h2>运行日志</h2><div class="btn-group"><label style="display:flex;align-items:center;gap:8px;font-size:12px;color:var(--text-muted);cursor:pointer"><input type="checkbox" id="autoScroll" checked> 自动滚动</label><button class="btn" onclick="confirmClearLogs()">🗑️ 清空</button></div></div>
                    <div class="log-container" id="logContainer"><div class="log-entry"><span class="time">[--:--:--]</span> 等待日志...</div></div>
                </div>
            </div>

            <!-- ========== 插件 ========== -->
            <div class="page" id="page-plugins">
                <div class="card">
                    <div class="card-header"><h2>已注册插件</h2><div class="btn-group"><button class="btn" onclick="refreshPlugins()">🔄 刷新</button><button class="btn" id="btnHotReload" onclick="toggleHotReload()">🔥 热重载</button></div></div>
                    <div class="table-wrapper">
                        <table><thead><tr><th>名称</th><th>版本</th><th>描述</th><th>类型</th><th>优先级</th><th>依赖</th><th>操作</th></tr></thead>
                        <tbody id="pluginList"><tr><td colspan="7" class="empty-state"><p>暂无已注册插件</p></td></tr></tbody></table>
                    </div>
                </div>
                <div class="card">
                    <div class="card-header"><h2>插件配置</h2></div>
                    <div id="pluginConfigPanel"><p style="color:var(--text-muted);text-align:center;padding:20px">点击插件列表中的 ⚙️ 按钮查看和编辑配置</p></div>
                </div>
                <div class="card">
                    <div class="card-header"><h2>加载插件</h2></div>
                    <div class="form-group"><label>插件目录路径</label><div style="display:flex;gap:8px"><input type="text" class="form-control" id="pluginDir" value="plugins" placeholder="plugins/"><button class="btn btn-primary" onclick="loadPlugins()">📂 加载</button></div></div>
                </div>
                <div class="card">
                    <div class="card-header"><h2>创建插件模板</h2></div>
                    <div class="form-row">
                        <div class="form-group"><label>插件名称</label><input type="text" class="form-control" id="newPluginName" placeholder="my_plugin"></div>
                        <div class="form-group"><label>类型</label><select class="form-control" id="newPluginType"><option value="enhancer">元数据增强</option><option value="parser">NFO解析</option><option value="generator">VSMETA生成</option><option value="filter">文件过滤</option><option value="lifecycle">生命周期</option></select></div>
                    </div>
                    <div class="form-row">
                        <div class="form-group"><label>作者</label><input type="text" class="form-control" id="newPluginAuthor" placeholder="Anonymous"></div>
                        <div class="form-group"><label>优先级</label><input type="number" class="form-control" id="newPluginPriority" value="50" min="0" max="100"></div>
                    </div>
                    <div class="form-group"><label>描述</label><input type="text" class="form-control" id="newPluginDesc" placeholder="插件功能描述"></div>
                    <button class="btn btn-primary" onclick="createPluginTemplate()">✨ 创建插件</button>
                </div>
            </div>
        </div>
    </div>

    <script>
        let csrfToken='';const SAFE_LEVELS=new Set(['info','warning','error','success','debug']);

        function switchTab(name){document.querySelectorAll('.tab').forEach(t=>{t.classList.toggle('active',t.dataset.tab===name)});document.querySelectorAll('.page').forEach(p=>p.classList.remove('active'));const page=document.getElementById('page-'+name);if(page)page.classList.add('active');if(name==='convert')refreshScanResults();if(name==='checkpoint')refreshCheckpoint();if(name==='backup')refreshBackups()}

        function showToast(message,type='info'){const c=document.getElementById('toastContainer');const icons={success:'✅',error:'❌',warning:'⚠️',info:'ℹ️'};const t=document.createElement('div');t.className='toast toast-'+type;t.innerHTML='<span class="toast-icon">'+(icons[type]||'ℹ️')+'</span><span>'+escHtml(message)+'</span>';c.appendChild(t);setTimeout(()=>{if(t.parentNode)t.parentNode.removeChild(t)},3000)}

        function showConfirm(title,message,onConfirm){const c=document.getElementById('modalContainer');c.innerHTML='<div class="modal-overlay" onclick="closeModal(event)"><div class="modal-box" onclick="event.stopPropagation()"><h3>'+escHtml(title)+'</h3><p>'+escHtml(message)+'</p><div class="modal-actions"><button class="btn" onclick="closeModal()">取消</button><button class="btn btn-danger" id="modalConfirmBtn">确认</button></div></div></div>';document.getElementById('modalConfirmBtn').onclick=()=>{closeModal();onConfirm()}}
        function closeModal(e){if(e&&e.target!==e.currentTarget)return;document.getElementById('modalContainer').innerHTML=''}

        function toggleTheme(){const h=document.documentElement;const n=h.getAttribute('data-theme')==='dark'?'light':'dark';h.setAttribute('data-theme',n);document.getElementById('themeToggle').textContent=n==='dark'?'🌙':'☀️';localStorage.setItem('theme',n)}
        (function(){const s=localStorage.getItem('theme');if(s){document.documentElement.setAttribute('data-theme',s);document.getElementById('themeToggle').textContent=s==='dark'?'🌙':'☀️'}const m=window.matchMedia('(prefers-color-scheme: light)');if(m.matches&&!s)toggleTheme()})();

        async function api(url,method='GET',data=null){const opts={method,headers:{'Content-Type':'application/json','X-CSRF-Token':csrfToken}};if(data)opts.body=JSON.stringify(data);const res=await fetch(url,opts);if(!res.ok){let d='';try{const j=await res.json();d=j.error||j.detail||''}catch(e){}throw new Error(d||'请求失败 ('+res.status+')')}return res.json()}

        function escHtml(s){if(s==null)return'';const d=document.createElement('div');d.textContent=String(s);return d.innerHTML}
        function formatSize(b){if(!b||b===0)return'-';if(b<1024)return b+'B';if(b<1048576)return(b/1024).toFixed(1)+'KB';if(b<1073741824)return(b/1048576).toFixed(1)+'MB';return(b/1073741824).toFixed(2)+'GB'}

        // === 仪表盘 ===
        async function refreshDashboard(){try{const data=await api('/api/status');const p=data.progress||{};document.getElementById('statTotal').textContent=p.total||0;document.getElementById('statProcessed').textContent=p.completed||0;document.getElementById('statSuccess').textContent=p.success||0;document.getElementById('statFailed').textContent=p.failed||0;document.getElementById('statSkipped').textContent=p.skipped||0;const rate=p.total>0?((p.success/p.total)*100).toFixed(1):'0';document.getElementById('statRate').textContent=rate+'%';const pct=p.total>0?((p.completed/p.total)*100):0;document.getElementById('progressBar').style.width=pct+'%';document.getElementById('progressPercent').textContent=Math.round(pct)+'%';document.getElementById('progressText').textContent=p.total>0?p.completed+' / '+p.total:'等待开始...';document.getElementById('progressDetail').textContent=p.current_file?'当前: '+escHtml(p.current_file):'';const dot=document.getElementById('statusDot');const txt=document.getElementById('statusText');if(data.is_running){dot.className='status-dot running';txt.textContent='运行中'}else{dot.className='status-dot idle';txt.textContent='就绪'}if(_wasRunning&&!data.is_running){showToast('转换已完成！','success');document.getElementById('btnStart').style.display='';document.getElementById('btnStop').style.display='none'}_wasRunning=!!data.is_running;if(data.recent_files&&data.recent_files.length>0){const tbody=document.getElementById('recentFiles');tbody.innerHTML=data.recent_files.map(f=>{const cls=f.result==='success'?'success':f.result==='error'?'danger':'warning';return '<tr><td>'+escHtml(f.file)+'</td><td style="max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">'+escHtml(f.dir)+'</td><td><span class="badge '+cls+'">'+escHtml(f.result)+'</span></td><td style="max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">'+escHtml(f.error||'')+'</td><td style="color:var(--text-muted)">'+escHtml(f.time||'')+'</td></tr>'}).join('')}}catch(e){console.error(e)}}

        // === 配置 ===
        const CFG_FIELDS={cfgDirectory:'directory',cfgWorkers:'max_workers',cfgMode:'process_mode',cfgMaxImgSize:'max_image_size_kb',cfgCompression:'image_compression_ratio',cfgRetries:'retry_attempts',cfgRetryDelay:'retry_delay',cfgInclude:'file_include_patterns',cfgExclude:'file_exclude_patterns',cfgRegex:'file_regex',cfgFormats:'output_formats',cfgMinSize:'min_size',cfgMaxSize:'max_size',cfgNfoExt:'nfo_extensions',cfgVideoExt:'video_extensions',cfgVsmetaExt:'vsmeta_extension',cfgBackupDir:'backup_dir',cfgCheckpointFile:'checkpoint_file',cfgReportDir:'report_output_dir',cfgImgCacheSize:'image_cache_max_size',cfgCheckpointInterval:'checkpoint_save_interval',cfgLogLevel:'log_level',cfgLogFile:'log_file',cfgLogFileMaxSize:'log_file_max_size',cfgLogFileBackupCount:'log_file_backup_count',cfgBackupMaxCount:'backup_max_count',cfgBackupMaxAge:'backup_max_age_days',cfgPluginDir:'plugin_dir',cfgAiKey:'ai_api_key',cfgAiUrl:'ai_api_url'};
        const LIST_FIELDS=new Set(['file_include_patterns','file_exclude_patterns','output_formats','nfo_extensions','video_extensions']);
        const BOOL_FIELDS={cfgOverwrite:'overwrite_existing',cfgBackup:'enable_backup',cfgDeleteVsmeta:'delete_existing_vsmeta',cfgDryRun:'dry_run',cfgTvShow:'tv_show_mode',cfgAutoLoadPlugins:'auto_load_plugins',cfgAiEnable:'enable_ai_completion'};
        const NUM_FIELDS=new Set(['max_workers','max_image_size_kb','retry_attempts','retry_delay','image_compression_ratio','min_size','max_size','log_file_max_size','log_file_backup_count','backup_max_count','backup_max_age_days','image_cache_max_size','checkpoint_save_interval']);

        async function loadConfig(){try{const data=await api('/api/config');const c=data.config||{};for(const[elId,field]of Object.entries(CFG_FIELDS)){const el=document.getElementById(elId);if(!el)continue;const v=c[field];if(v===undefined||v===null)continue;if(LIST_FIELDS.has(field)){el.value=Array.isArray(v)?v.join(', '):''}else{el.value=v}}for(const[elId,field]of Object.entries(BOOL_FIELDS)){const el=document.getElementById(elId);if(el)el.checked=!!c[field]}showToast('配置已加载','info')}catch(e){showToast('加载失败: '+e.message,'error')}}
        function resetConfig(){showConfirm('重置配置','确定要恢复所有配置为默认值吗？',async()=>{try{await api('/api/config','POST',{});loadConfig();showToast('配置已重置','success')}catch(e){showToast('重置失败: '+e.message,'error')}})}
        function getConfigFromForm(){const cfg={};for(const[elId,field]of Object.entries(CFG_FIELDS)){const el=document.getElementById(elId);if(!el)continue;const v=el.value;if(!v&&v!=='0')continue;if(LIST_FIELDS.has(field)){cfg[field]=v.split(',').map(s=>s.trim()).filter(Boolean)||null}else if(NUM_FIELDS.has(field)){cfg[field]=parseFloat(v)||0}else{cfg[field]=v}}for(const[elId,field]of Object.entries(BOOL_FIELDS)){const el=document.getElementById(elId);if(el)cfg[field]=el.checked}return cfg}
        async function saveConfig(){try{await api('/api/config','POST',getConfigFromForm());showToast('配置已保存','success')}catch(e){showToast('保存失败: '+e.message,'error')}}
        function exportConfig(){window.location.href='/api/config/export?token='+encodeURIComponent(csrfToken)}
        function importConfig(){showConfirm('导入配置','将上传一个 JSON 配置文件并覆盖当前配置。确定继续？',()=>{const input=document.createElement('input');input.type='file';input.accept='.json';input.onchange=async(e)=>{const file=e.target.files[0];if(!file)return;try{const text=await file.text();const data=JSON.parse(text);await api('/api/config/import','POST',data);loadConfig();showToast('配置已导入','success')}catch(err){showToast('导入失败: '+err.message,'error')}};input.click()})}

        // === 智能助手 ===
        function setSmartCommand(cmd){document.getElementById('smartCommand').value=cmd}
        async function executeSmartCommand(){const cmd=document.getElementById('smartCommand').value.trim();if(!cmd){showToast('请输入命令','warning');return}try{showToast('正在解析命令...','info');const data=await api('/api/smart/parse','POST',{command:cmd});if(data.config){for(const[key,val]of Object.entries(data.config)){const elId=Object.entries(CFG_FIELDS).find(([,f])=>f===key)?.[0];if(elId){const el=document.getElementById(elId);if(el){if(LIST_FIELDS.has(key)){el.value=Array.isArray(val)?val.join(', '):val}else if(typeof val==='boolean'){el.checked=val}else{el.value=val}}}for(const[elId,field]of Object.entries(BOOL_FIELDS)){if(data.config[field]!==undefined){const el=document.getElementById(elId);if(el)el.checked=!!data.config[field]}}}document.getElementById('smartResult').innerHTML='<div class="stat-card" style="border-left:3px solid var(--success)"><div class="label">解析成功</div><div style="font-size:13px;color:var(--text-secondary)">'+escHtml(data.message)+'</div></div>';showToast('配置已更新','success')}else{showToast('无法解析命令','error')}}catch(e){showToast('解析失败: '+e.message,'error')}}

        // === 转换 ===
        async function startConversion(selectedOnly=false){try{const cfg=getConfigFromForm();if(selectedOnly){const selected=Array.from(document.querySelectorAll('.file-select[data-file]:checked')).map(cb=>cb.dataset.file);if(selected.length===0){showToast('请先选择文件','warning');return}cfg.selected_files=selected}await api('/api/convert/start','POST',cfg);document.getElementById('btnStart').style.display='none';document.getElementById('btnStop').style.display='';document.getElementById('convertStatus').innerHTML='<div class="icon">⏳</div><p>转换进行中...</p>';showToast('转换任务已启动','success')}catch(e){showToast('启动失败: '+e.message,'error')}}
        function confirmStopConversion(){showConfirm('停止转换','确定要停止正在进行的转换任务吗？',stopConversion)}
        async function stopConversion(){try{await api('/api/convert/stop','POST');document.getElementById('btnStart').style.display='';document.getElementById('btnStop').style.display='none';showToast('已发送停止信号','warning')}catch(e){showToast('停止失败: '+e.message,'error')}}

        // === 扫描结果 ===
        async function refreshScanResults(){try{const data=await api('/api/scan-results');const tbody=document.getElementById('scanResults');const files=data.files||[];document.getElementById('scanCount').textContent=files.length?'共 '+files.length+' 个文件':'';if(files.length>0){tbody.innerHTML=files.map((f,i)=>'<tr><td><input type="checkbox" class="file-select" data-file="'+escHtml(f.directory+'/'+f.filename)+'" onchange="updateSelectedFiles()"></td><td>'+(i+1)+'</td><td>'+escHtml(f.filename)+'</td><td style="max-width:250px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">'+escHtml(f.directory)+'</td><td>'+formatSize(f.size)+'</td><td><span class="badge '+(f.has_nfo?'success':'warning')+'">'+(f.has_nfo?'有NFO':'无NFO')+'</span></td><td>'+(f.selected?'<span class="badge info">已选</span>':'')+'</td></tr>').join('')}else{tbody.innerHTML='<tr><td colspan="7" class="empty-state"><p>暂无扫描结果</p></td></tr>'}}catch(e){console.error(e)}}
        function toggleSelectAll(cb){document.querySelectorAll('.file-select[data-file]').forEach(c=>c.checked=cb.checked);updateSelectedFiles()}
        function selectAllFiles(){document.querySelectorAll('.file-select[data-file]').forEach(c=>c.checked=true);updateSelectedFiles()}
        function deselectAllFiles(){document.querySelectorAll('.file-select[data-file]').forEach(c=>c.checked=false);updateSelectedFiles()}
        function updateSelectedFiles(){const selected=Array.from(document.querySelectorAll('.file-select[data-file]:checked')).map(cb=>cb.dataset.file);api('/api/scan-results/select','POST',{files:selected}).catch(()=>{})}

        // === 工具箱 ===
        async function validateNfo(){const path=document.getElementById('nfoPath').value.trim();if(!path){showToast('请输入 NFO 文件路径','warning');return}try{const data=await api('/api/tools/validate-nfo','POST',{path:path});const el=document.getElementById('nfoValidationResult');if(data.valid){el.innerHTML='<div class="stat-card" style="border-left:3px solid var(--success)"><div class="label">✅ NFO 格式正确</div><div style="font-size:13px;color:var(--text-secondary)">标题: '+escHtml(data.title||'N/A')+'<br>年份: '+escHtml(data.year||'N/A')+'<br>评分: '+escHtml(data.rating||'N/A')+'</div></div>'}else{el.innerHTML='<div class="stat-card" style="border-left:3px solid var(--danger)"><div class="label">❌ NFO 格式错误</div><div style="font-size:13px;color:var(--text-secondary)">'+escHtml(data.error||'未知错误')+'</div></div>'}}catch(e){showToast('验证失败: '+e.message,'error')}}
        async function previewVsmeta(){const path=document.getElementById('vsmetaPath').value.trim();if(!path){showToast('请输入 VSMETA 文件路径','warning');return}try{const data=await api('/api/tools/preview-vsmeta','POST',{path:path});const el=document.getElementById('vsmetaPreviewResult');if(data.success){el.innerHTML='<div class="stat-card"><div class="label">📄 VSMETA 内容</div><pre style="font-size:12px;overflow-x:auto;background:var(--bg-input);padding:12px;border-radius:8px;margin-top:8px">'+escHtml(JSON.stringify(data.metadata,null,2))+'</pre></div>'}else{el.innerHTML='<div class="stat-card" style="border-left:3px solid var(--danger)"><div class="label">❌ 解析失败</div><div style="font-size:13px;color:var(--text-secondary)">'+escHtml(data.error)+'</div></div>'}}catch(e){showToast('预览失败: '+e.message,'error')}}

        // === 报告 ===
        async function generateReport(fmt){try{showToast('正在生成 '+fmt.toUpperCase()+' 报告...','info');const data=await api('/api/report/generate','POST',{format:fmt});if(data.filepath){showToast('报告已生成','success');document.getElementById('reportContent').innerHTML='<div style="text-align:center;padding:20px"><p style="margin-bottom:12px">📄 报告已生成</p><p style="color:var(--text-muted);font-family:JetBrains Mono,monospace;font-size:13px">'+escHtml(data.filepath)+'</p><p style="margin-top:12px"><a href="/api/report/download?format='+fmt+'" class="btn btn-primary" style="text-decoration:none;display:inline-block">⬇️ 下载报告</a></p></div>'}else{showToast('无数据可生成报告','warning')}}catch(e){showToast('生成失败: '+e.message,'error')}}
        async function generateAdvancedReport(type,fmt){try{showToast('正在生成报告...','info');const data=await api('/api/report/'+type,'POST',{format:fmt});if(data.filepath){showToast('报告已生成','success');document.getElementById('advancedReportContent').innerHTML='<div style="text-align:center;padding:20px"><p style="margin-bottom:12px">📊 报告已生成</p><p style="color:var(--text-muted);font-family:JetBrains Mono,monospace;font-size:13px">'+escHtml(data.filepath)+'</p></div>'}else{showToast('无数据可生成报告','warning')}}catch(e){showToast('生成失败: '+e.message,'error')}}

        // === 断点 ===
        async function refreshCheckpoint(){try{const data=await api('/api/checkpoint');const el=document.getElementById('checkpointInfo');if(data.error){el.innerHTML='<div class="empty-state"><div class="icon">💾</div><p>'+escHtml(data.error)+'</p></div>';return}const cp=data.checkpoint||{};el.innerHTML='<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:16px;margin-bottom:20px"><div class="stat-card"><div class="label">断点文件</div><div class="value" style="font-size:14px;word-break:break-all">'+escHtml(cp.filepath||'-')+'</div></div><div class="stat-card"><div class="label">已完成文件</div><div class="value success">'+(cp.completed_count||0)+'</div></div><div class="stat-card"><div class="label">失败文件</div><div class="value danger">'+(cp.failed_count||0)+'</div></div><div class="stat-card"><div class="label">最后更新</div><div class="value" style="font-size:14px">'+escHtml(cp.last_updated||'-')+'</div></div></div>'+(cp.completed_files&&cp.completed_files.length>0?'<div class="card-header"><h2>已完成文件列表</h2></div><div class="table-wrapper"><table><thead><tr><th>文件路径</th><th>状态</th></tr></thead><tbody>'+cp.completed_files.map(f=>'<tr><td style="font-family:JetBrains Mono,monospace;font-size:12px">'+escHtml(f.filepath)+'</td><td><span class="badge '+(f.status==='completed'?'success':'danger')+'">'+escHtml(f.status)+'</span></td></tr>').join('')+'</tbody></table></div>':'')}catch(e){showToast('获取断点失败: '+e.message,'error')}}
        function confirmResetCheckpoint(){showConfirm('重置断点','确定要清除所有断点记录吗？下次转换将重新处理所有文件。',async()=>{try{await api('/api/checkpoint','DELETE');refreshCheckpoint();showToast('断点已重置','success')}catch(e){showToast('重置失败: '+e.message,'error')}})}
        async function retryFailed(type){const labels={all:'全部',nfo_missing:'NFO 缺失',error:'转换错误',delete_failed:'删除失败'};showConfirm('重试失败文件','确定要重试所有"'+(labels[type]||type)+'"类型的失败文件吗？',async()=>{try{const data=await api('/api/retry-failed','POST',{type:type});showToast('已标记 '+data.count+' 个文件待重试','success');refreshCheckpoint()}catch(e){showToast('重试失败: '+e.message,'error')}})}

        // === 备份 ===
        async function refreshBackups(){try{const data=await api('/api/backups');const tbody=document.getElementById('backupList');const files=data.files||[];if(files.length>0){tbody.innerHTML=files.map(f=>'<tr><td style="font-family:JetBrains Mono,monospace;font-size:12px">'+escHtml(f.name)+'</td><td>'+formatSize(f.size)+'</td><td style="color:var(--text-muted)">'+escHtml(f.modified)+'</td><td><button class="btn btn-danger btn-sm" data-backup="'+encodeURIComponent(f.path)+'" onclick="deleteBackup(this)">删除</button></td></tr>').join('')}else{tbody.innerHTML='<tr><td colspan="4" class="empty-state"><p>暂无备份文件</p></td></tr>'}}catch(e){console.error(e)}}
        async function deleteBackup(btn){const path=decodeURIComponent(btn.dataset.backup);showConfirm('删除备份','确定要删除此备份文件吗？',async()=>{try{await api('/api/backups/delete','POST',{path:path});refreshBackups();showToast('备份已删除','success')}catch(e){showToast('删除失败: '+e.message,'error')}})}
        function confirmCleanBackups(){showConfirm('清理过期备份','将根据配置的备份策略清理过期备份，确定继续？',async()=>{try{const data=await api('/api/backups/clean','POST');showToast('已清理 '+data.deleted+' 个备份文件','success');refreshBackups()}catch(e){showToast('清理失败: '+e.message,'error')}})}

        // === 日志 ===
        async function refreshLogs(){try{const data=await api('/api/logs');const c=document.getElementById('logContainer');if(data.logs&&data.logs.length>0){const auto=document.getElementById('autoScroll').checked;const near=c.scrollHeight-c.scrollTop-c.clientHeight<80;c.innerHTML=data.logs.map(l=>{const sl=SAFE_LEVELS.has(l.level)?l.level:'info';return '<div class="log-entry"><span class="time">['+escHtml(l.time)+']</span> <span class="level-'+sl+'">['+sl.toUpperCase()+']</span> '+escHtml(l.message)+'</div>'}).join('');if(auto&&near)c.scrollTop=c.scrollHeight}}catch(e){console.error(e)}}
        function confirmClearLogs(){showConfirm('清空日志','确定要清空所有日志记录吗？',clearLogs)}
        async function clearLogs(){try{await api('/api/logs','DELETE');document.getElementById('logContainer').innerHTML='';showToast('日志已清空','info')}catch(e){showToast('清空失败: '+e.message,'error')}}

        // === 插件 ===
        async function refreshPlugins(){try{const data=await api('/api/plugins');const tbody=document.getElementById('pluginList');const plugins=data.plugins||[];if(plugins.length>0){tbody.innerHTML=plugins.map(p=>{const sn=encodeURIComponent(p.name);const deps=(p.dependencies||[]).length?escHtml((p.dependencies||[]).join(', ')):'<span style="color:var(--text-muted)">无</span>';const pri=p.priority!==undefined?p.priority:50;const priColor=pri>=75?'var(--success)':pri>=25?'var(--text-primary)':'var(--warning)';return '<tr><td><strong>'+escHtml(p.name)+'</strong></td><td style="font-family:JetBrains Mono,monospace;font-size:12px">'+escHtml(p.version)+'</td><td style="max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">'+escHtml(p.description)+'</td><td><span class="badge info">'+escHtml(p.type)+'</span></td><td style="color:'+priColor+';font-weight:600">'+pri+'</td><td style="font-size:12px;max-width:150px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">'+deps+'</td><td><div class="btn-group" style="gap:4px"><button class="btn btn-sm" title="配置" onclick="editPluginConfig(\''+sn+'\')">⚙️</button><button class="btn btn-sm" title="重载" onclick="reloadPlugin(\''+sn+'\')">🔄</button><button class="btn btn-danger btn-sm" title="卸载" data-plugin-name="'+sn+'" onclick="unloadPlugin(this)">✕</button></div></td></tr>'}).join('')}else{tbody.innerHTML='<tr><td colspan="7" class="empty-state"><p>暂无已注册插件</p></td></tr>'}}catch(e){console.error(e)}}
        async function unloadPlugin(btn){const name=decodeURIComponent(btn.dataset.pluginName);showConfirm('卸载插件','确定要卸载插件 "'+name+'" 吗？',async()=>{try{await api('/api/plugins/unload','POST',{name:name});showToast('已卸载: '+name,'info');refreshPlugins()}catch(e){showToast('卸载失败: '+e.message,'error')}})}
        async function loadPlugins(){const dir=document.getElementById('pluginDir').value.trim();if(!dir){showToast('请输入插件目录','warning');return}try{const data=await api('/api/plugins/load','POST',{directory:dir});showToast('已加载 '+(data.count||0)+' 个插件','success');refreshPlugins()}catch(e){showToast('加载失败: '+e.message,'error')}}
        async function editPluginConfig(name){try{const data=await api('/api/plugins/'+name+'/config');const panel=document.getElementById('pluginConfigPanel');const schema=data.schema||{};const config=data.config||{};let html='<div style="margin-bottom:12px"><strong>📦 '+escHtml(name)+'</strong></div>';const keys=Object.keys(schema);if(keys.length>0){html+='<form id="pluginConfigForm">';keys.forEach(key=>{const s=schema[key];const val=config[key]!==undefined?config[key]:s.default!==undefined?s.default:'';const ek=escHtml(key);html+='<div class="form-group"><label>'+escHtml(s.description||key)+'</label>';if(s.type==='bool'){html+='<label style="display:flex;align-items:center;gap:8px;cursor:pointer"><input type="checkbox" id="pcfg_'+ek+'" '+(val?'checked':'')+'>'+escHtml(String(val))+'</label>'}else if(s.type==='int'||s.type==='float'){const mn=s.min!==undefined?' min="'+escHtml(String(s.min))+'"':'';const mx=s.max!==undefined?' max="'+escHtml(String(s.max))+'"':'';html+='<input type="number" class="form-control" id="pcfg_'+ek+'" value="'+escHtml(String(val))+'"'+mn+mx+'>'}else if(s.type==='list'){html+='<input type="text" class="form-control" id="pcfg_'+ek+'" value="'+escHtml(Array.isArray(val)?val.join(', '):String(val))+'" placeholder="逗号分隔">'}else{html+='<input type="text" class="form-control" id="pcfg_'+ek+'" value="'+escHtml(String(val))+'"'}html+='</div>'});html+='<div class="btn-group"><button type="button" class="btn btn-primary" onclick="savePluginConfig(\''+encodeURIComponent(name)+'\')">💾 保存</button><button type="button" class="btn" onclick="editPluginConfig(\''+encodeURIComponent(name)+'\')">🔄 刷新</button></div></form>'}else{html+='<p style="color:var(--text-muted)">此插件没有可配置项</p>';if(Object.keys(config).length>0){html+='<div style="margin-top:8px"><strong>当前配置:</strong><pre style="font-size:12px;background:var(--bg-input);padding:8px;border-radius:6px;margin-top:4px;overflow-x:auto">'+escHtml(JSON.stringify(config,null,2))+'</pre></div>'}}panel.innerHTML=html}catch(e){showToast('获取配置失败: '+e.message,'error')}}
        async function savePluginConfig(encName){const name=decodeURIComponent(encName);const form=document.getElementById('pluginConfigForm');if(!form)return;const data={};form.querySelectorAll('input[id^="pcfg_"]').forEach(inp=>{const key=inp.id.replace('pcfg_','').trim();if(inp.type==='checkbox'){data[key]=inp.checked}else if(inp.type==='number'){data[key]=parseFloat(inp.value)||0}else{data[key]=inp.value}});try{await api('/api/plugins/'+name+'/config','POST',data);showToast('配置已保存','success');editPluginConfig(name)}catch(e){showToast('保存失败: '+e.message,'error')}}
        async function reloadPlugin(name){try{await api('/api/plugins/'+name+'/reload','POST');showToast('已重载: '+name,'success');refreshPlugins()}catch(e){showToast('重载失败: '+e.message,'error')}}
        async function toggleHotReload(){try{const btn=document.getElementById('btnHotReload');const isOn=btn.classList.contains('active');const res=await api('/api/plugins/hot-reload','POST',{enabled:!isOn});if(res.enabled){btn.classList.add('active');btn.textContent='🔥 热重载 ON';showToast('热重载已启用','success')}else{btn.classList.remove('active');btn.textContent='🔥 热重载';showToast('热重载已禁用','info')}}catch(e){showToast('操作失败: '+e.message,'error')}}
        async function createPluginTemplate(){const name=document.getElementById('newPluginName').value.trim();if(!name){showToast('请输入插件名称','warning');return}const type=document.getElementById('newPluginType').value;try{const data=await api('/api/plugins/create','POST',{name:name,type:type,author:document.getElementById('newPluginAuthor').value.trim()||'Anonymous',priority:parseInt(document.getElementById('newPluginPriority').value)||50,description:document.getElementById('newPluginDesc').value.trim()});showToast('插件模板已创建: '+data.path,'success');document.getElementById('newPluginName').value='';document.getElementById('newPluginDesc').value='';document.getElementById('newPluginAuthor').value='';document.getElementById('newPluginPriority').value='50';refreshPlugins()}catch(e){showToast('创建失败: '+e.message,'error')}}

        // === 智能轮询 ===
        let pollTimer=null,pollInterval=5000,_wasRunning=false;
        function startPolling(){if(pollTimer)clearInterval(pollTimer);pollTimer=setInterval(async()=>{await refreshDashboard();await refreshLogs();await refreshScanResults();const dot=document.getElementById('statusDot');const running=dot&&dot.classList.contains('running');const ni=running?1000:5000;if(ni!==pollInterval){pollInterval=ni;startPolling()}},pollInterval)}

        // === 键盘快捷键 ===
        document.addEventListener('keydown',e=>{if(e.ctrlKey&&e.key==='s'){e.preventDefault();saveConfig()}else if(e.ctrlKey&&e.key==='r'){e.preventDefault();refreshDashboard()}else if(e.ctrlKey&&e.key==='Enter'){e.preventDefault();if(document.getElementById('btnStart').style.display!=='none')startConversion()}else if(e.key==='Escape'){closeModal()}else if(e.key==='t'||e.key==='T'){if(e.target.tagName!=='INPUT'&&e.target.tagName!=='TEXTAREA')toggleTheme()}else if(e.key>='1'&&e.key<='9'){const tabs=['dashboard','config','smart','convert','tools','report','checkpoint','backup','logs','plugins'];const idx=parseInt(e.key)-1;if(tabs[idx]){e.preventDefault();switchTab(tabs[idx])}}});

        // === 页面可见性检测 ===
        document.addEventListener('visibilitychange',()=>{if(document.hidden){if(pollTimer)clearInterval(pollTimer);pollTimer=setInterval(async()=>{await refreshDashboard();await refreshLogs()},10000)}else{startPolling()}});

        // === 初始化 ===
        (async function(){try{const s=await api('/api/status');csrfToken=s.csrf_token||''}catch(e){console.error(e)}loadConfig();refreshDashboard();refreshPlugins();startPolling()})();
    </script>
</body>
</html>'''


# ============================================================================
# API 路由
# ============================================================================

@app.route('/')
def index() -> str:
    return render_template_string(INDEX_HTML)


@app.route('/api/status')
@require_api_token
def api_status() -> Dict:
    with _state_lock:
        p = _state['progress'].copy()
        is_running = _state['is_running']
        csrf_token = _state['csrf_token']
    recent = []
    converter = _state.get('converter')
    if converter and hasattr(converter, 'report_details'):
        recent = converter.report_details[-20:]
    return jsonify({'is_running': is_running, 'progress': p, 'recent_files': recent, 'csrf_token': csrf_token})


@app.route('/api/config', methods=['GET'])
@require_api_token
def api_get_config() -> Dict:
    config = _get_state('config')
    if config and is_dataclass(config):
        return jsonify({'config': asdict(config)})
    return jsonify({'config': {}})


@app.route('/api/config', methods=['POST'])
@require_api_token
@require_csrf
def api_set_config() -> Tuple:
    data = request.get_json(silent=True)
    if data is not None and isinstance(data, dict) and (len(data) == 0 or data.get('reset')):
        try:
            from nfo_to_vsmeta_converter_complete import Config
            config = Config()
            _set_state('config', config)
            converter = _get_state('converter')
            if converter:
                converter.config = config
            _add_log('info', '配置已重置为默认值')
            return jsonify({'success': True})
        except Exception as e:
            return jsonify({'error': f'重置失败: {e}'}), 500

    validated, error = _validate_config_data(data)
    if error and not validated:
        return jsonify({'error': error}), 400
    try:
        from nfo_to_vsmeta_converter_complete import Config
        existing = _get_state('config')
        if existing and is_dataclass(existing):
            d = asdict(existing)
            d.update(validated)
            config = Config(**d)
        else:
            config = Config(**validated)
        _set_state('config', config)
        converter = _get_state('converter')
        if converter:
            converter.config = config
        _add_log('info', '配置已更新')
        return jsonify({'success': True})
    except TypeError as e:
        return jsonify({'error': f'配置参数错误: {e}'}), 400
    except Exception as e:
        _add_log('error', f'更新配置失败: {e}')
        return jsonify({'error': f'内部错误: {e}'}), 500


@app.route('/api/smart/parse', methods=['POST'])
@require_api_token
@require_csrf
def api_smart_parse() -> Tuple:
    """智能助手：解析自然语言命令"""
    data = request.get_json(silent=True) or {}
    command = str(data.get('command', '')).strip().lower()
    if not command:
        return jsonify({'error': '命令不能为空'}), 400

    try:
        config_updates = {}
        message_parts = []

        # 解析年份过滤
        import re
        year_match = re.search(r'(\d{4})\s*年?\s*(?:以后|之后|>)', command)
        if year_match:
            year = year_match.group(1)
            config_updates['file_regex'] = f'.*{year}.*'
            message_parts.append(f'年份过滤: {year}年以后')

        # 解析文件扩展名
        ext_match = re.findall(r'(mp4|mkv|avi|ts|wmv)', command, re.I)
        if ext_match:
            exts = [f'.{e.lower()}' for e in set(ext_match)]
            config_updates['video_extensions'] = exts
            message_parts.append(f'视频格式: {", ".join(exts)}')

        # 解析线程数
        thread_match = re.search(r'(\d+)\s*个?\s*(?:线程|workers?)', command)
        if thread_match:
            workers = int(thread_match.group(1))
            config_updates['max_workers'] = max(1, min(32, workers))
            message_parts.append(f'线程数: {workers}')

        # 解析图片压缩
        compress_match = re.search(r'(\d+)%?\s*(?:质量|压缩|quality)', command)
        if compress_match:
            quality = int(compress_match.group(1))
            config_updates['image_compression_ratio'] = max(0.1, min(1.0, quality / 100))
            message_parts.append(f'图片质量: {quality}%')

        # 解析文件大小
        size_match = re.search(r'(大于|超过)\s*(\d+)\s*(GB?|MB?|字节)', command)
        if size_match:
            size = int(size_match.group(2))
            unit = size_match.group(3).upper()
            if 'G' in unit:
                size_bytes = size * 1073741824
            elif 'M' in unit:
                size_bytes = size * 1048576
            else:
                size_bytes = size
            config_updates['min_size'] = size_bytes
            message_parts.append(f'最小文件大小: {size}{unit}')

        # 解析开关选项
        if '备份' in command or 'backup' in command:
            if '不' in command or '禁用' in command or '关闭' in command:
                config_updates['enable_backup'] = False
                message_parts.append('禁用备份')
            else:
                config_updates['enable_backup'] = True
                message_parts.append('启用备份')

        if '剧集' in command or 'tv show' in command or '电视剧' in command:
            config_updates['tv_show_mode'] = True
            message_parts.append('启用剧集模式')

        if '预演' in command or 'dry run' in command or '测试' in command:
            config_updates['dry_run'] = True
            message_parts.append('启用预演模式')

        if '覆盖' in command or 'overwrite' in command:
            if '不' in command:
                config_updates['overwrite_existing'] = False
            else:
                config_updates['overwrite_existing'] = True
                message_parts.append('允许覆盖已有文件')

        if not message_parts:
            return jsonify({'error': '无法解析命令，请尝试使用示例中的格式'}), 400

        return jsonify({
            'success': True,
            'config': config_updates,
            'message': '已应用: ' + '、'.join(message_parts)
        })
    except Exception as e:
        return jsonify({'error': f'解析失败: {e}'}), 500


@app.route('/api/convert/start', methods=['POST'])
@require_api_token
@require_csrf
def api_start_conversion() -> Tuple:
    if _get_state('is_running'):
        return jsonify({'error': '转换正在进行中'}), 400
    data = request.get_json(silent=True)
    validated, error = _validate_config_data(data)
    if error and not validated:
        return jsonify({'error': error}), 400

    # 处理批量选择
    selected_files = data.get('selected_files', []) if data else []

    try:
        from nfo_to_vsmeta_converter_complete import Config, NFOToVSMETAConverter
        existing = _get_state('config')
        if existing and is_dataclass(existing):
            d = asdict(existing)
            d.update(validated)
            config = Config(**d)
        else:
            config = Config(**validated)
        _set_state('config', config)
        _set_state('is_running', True)
        _update_progress({'total': 0, 'completed': 0, 'success': 0, 'failed': 0, 'skipped': 0,
                          'current_file': '', 'start_time': datetime.now().isoformat(), 'end_time': None})

        def run_conversion() -> None:
            try:
                converter = NFOToVSMETAConverter(config)
                _set_state('converter', converter)
                files = converter.file_scanner.scan()

                # 如果有批量选择，只处理选中的文件
                if selected_files:
                    files = [(d, f) for d, f in files if f'{d}/{f}' in selected_files]

                total = len(files)
                _update_progress({'total': total})

                scan_data = []
                for d, f in files:
                    fp = os.path.join(d, f)
                    nfo_found = any(os.path.exists(fp + ext) for ext in (config.nfo_extensions or ['.nfo']))
                    size = 0
                    try: size = os.path.getsize(fp)
                    except OSError: pass
                    scan_data.append({'filename': f, 'directory': d, 'size': size, 'has_nfo': nfo_found, 'selected': f'{d}/{f}' in selected_files})
                _set_state('scan_results', scan_data)

                if not files:
                    _add_log('warning', '未找到需要处理的视频文件'); return

                pending = [(d, f) for d, f in files if not converter.checkpoint.is_completed(os.path.join(d, f))]
                if len(pending) < total:
                    _add_log('info', f'跳过 {total - len(pending)} 个已处理文件')
                if not pending:
                    _add_log('success', '所有文件已处理完成！'); return

                converter.plugin_manager.notify_lifecycle('on_start', config=config)

                for directory, filename in pending:
                    if not _get_state('is_running'):
                        _add_log('warning', '转换已被用户停止'); break
                    filepath = os.path.join(directory, filename)
                    _update_progress({'current_file': filename})
                    converter.plugin_manager.notify_lifecycle('on_file_start', filepath=filepath)
                    try:
                        result = converter._process_with_retry(directory, filename)
                        converter._update_stats(result, directory, filename)
                        r = result.get('result', 'error' if not result.get('success') else 'success')
                        with _state_lock:
                            if r == 'success': _state['progress']['success'] += 1
                            elif r == 'skipped': _state['progress']['skipped'] += 1
                            else: _state['progress']['failed'] += 1
                        _add_log('info', f'[{r}] {filename}')
                    except Exception as e:
                        with _state_lock: _state['progress']['failed'] += 1
                        converter._update_stats({'success': False, 'error': str(e)}, directory, filename)
                        _add_log('error', f'[error] {filename}: {e}')
                    with _state_lock: _state['progress']['completed'] += 1

                if converter._interrupted:
                    converter.checkpoint.force_save()
                    _add_log('warning', '进度已保存（中断）')
                converter.stats.end_time = datetime.now()
                converter.plugin_manager.notify_lifecycle('on_finish', stats=converter.stats)
                converter.checkpoint.shutdown()
                p = _get_state('progress')
                _add_log('success', f"转换完成！成功: {p['success']}, 失败: {p['failed']}, 跳过: {p['skipped']}")
            except Exception as e:
                _add_log('error', f'转换出错: {e}')
                logger.error(f'转换线程异常: {e}', exc_info=True)
            finally:
                _set_state('is_running', False)
                _update_progress({'current_file': '', 'end_time': datetime.now().isoformat()})

        threading.Thread(target=run_conversion, daemon=True).start()
        return jsonify({'success': True, 'message': '转换已启动'})
    except ImportError as e:
        return jsonify({'error': f'模块导入失败: {e}'}), 500
    except Exception as e:
        _set_state('is_running', False)
        return jsonify({'error': f'启动失败: {e}'}), 500


@app.route('/api/convert/stop', methods=['POST'])
@require_api_token
@require_csrf
def api_stop_conversion() -> Dict:
    _set_state('is_running', False)
    converter = _get_state('converter')
    if converter and hasattr(converter, '_interrupted'):
        converter._interrupted = True
    _add_log('warning', '已发送停止信号')
    return jsonify({'success': True})


@app.route('/api/scan-results')
@require_api_token
def api_get_scan_results() -> Dict:
    results = _get_state('scan_results', [])
    return jsonify({'files': results})


@app.route('/api/scan-results/select', methods=['POST'])
@require_api_token
@require_csrf
def api_select_scan_results() -> Dict:
    """更新选中的文件列表"""
    data = request.get_json(silent=True) or {}
    files = data.get('files', [])
    _set_state('selected_files', files)
    return jsonify({'success': True, 'selected': len(files)})


@app.route('/api/logs')
@require_api_token
def api_get_logs() -> Dict:
    with _state_lock:
        logs = list(_state['logs'])
    return jsonify({'logs': logs})


@app.route('/api/logs', methods=['DELETE'])
@require_api_token
@require_csrf
def api_clear_logs() -> Dict:
    with _state_lock:
        _state['logs'] = []
    return jsonify({'success': True})


# ============================================================================
# 工具箱 API
# ============================================================================

@app.route('/api/tools/validate-nfo', methods=['POST'])
@require_api_token
@require_csrf
def api_validate_nfo() -> Tuple:
    """验证 NFO 文件"""
    data = request.get_json(silent=True) or {}
    path = str(data.get('path', ''))
    if not path or not os.path.isfile(path):
        return jsonify({'error': '文件不存在'}), 404
    if not _validate_path(path, allow_absolute=True):
        return jsonify({'error': '路径不安全'}), 403
    try:
        import xml.etree.ElementTree as ET
        tree = ET.parse(path)
        root = tree.getroot()
        result = {'valid': True}
        # 提取常用字段
        for field in ['title', 'year', 'rating', 'plot', 'runtime']:
            elem = root.find(f'./{field}')
            if elem is not None and elem.text:
                result[field] = elem.text.strip()
        return jsonify(result)
    except ET.ParseError as e:
        return jsonify({'valid': False, 'error': f'XML 解析错误: {e}'}), 400
    except Exception as e:
        return jsonify({'valid': False, 'error': str(e)}), 500


@app.route('/api/tools/preview-vsmeta', methods=['POST'])
@require_api_token
@require_csrf
def api_preview_vsmeta() -> Tuple:
    """预览 VSMETA 文件内容"""
    data = request.get_json(silent=True) or {}
    path = str(data.get('path', ''))
    if not path or not os.path.isfile(path):
        return jsonify({'error': '文件不存在'}), 404
    if not _validate_path(path, allow_absolute=True):
        return jsonify({'error': '路径不安全'}), 403
    try:
        # 读取并解析 VSMETA 文件
        with open(path, 'rb') as f:
            content = f.read()
        # 简单解析：提取可读的字符串
        import re
        strings = re.findall(rb'[\x20-\x7e]{4,}', content)
        decoded = [s.decode('utf-8', errors='ignore') for s in strings]
        return jsonify({
            'success': True,
            'metadata': {
                'file_size': len(content),
                'readable_strings': decoded[:50],
                'hex_preview': content[:100].hex()
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# 报告 API
# ============================================================================

@app.route('/api/report/generate', methods=['POST'])
@require_api_token
@require_csrf
def api_generate_report() -> Tuple:
    data = request.get_json(silent=True) or {}
    fmt = str(data.get('format', 'html')).lower()
    if fmt not in _ALLOWED_REPORT_FORMATS:
        return jsonify({'error': f'不支持的报告格式: {fmt}'}), 400
    converter = _get_state('converter')
    if not converter or not hasattr(converter, 'report_details') or not converter.report_details:
        return jsonify({'error': '暂无转换数据，请先执行转换'}), 400
    try:
        from nfo_to_vsmeta_converter_complete import ReportGenerator
        rg = ReportGenerator(converter)
        report_dir = converter.config.report_output_dir or _PROJECT_ROOT
        os.makedirs(report_dir, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'conversion_report_{timestamp}.{fmt}'
        filepath = os.path.join(report_dir, filename)
        if fmt == 'html':
            content = rg.generate_html(converter.report_details, converter.stats)
        elif fmt == 'csv':
            content = rg.generate_csv(converter.report_details)
        else:
            content = rg.generate_txt(converter.report_details, converter.stats)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        _add_log('success', f'报告已生成: {filepath}')
        return jsonify({'success': True, 'filepath': filepath, 'filename': filename})
    except Exception as e:
        _add_log('error', f'生成报告失败: {e}')
        return jsonify({'error': f'生成报告失败: {e}'}), 500


@app.route('/api/report/download')
@require_api_token
def api_download_report():
    fmt = request.args.get('format', 'html').lower()
    if fmt not in _ALLOWED_REPORT_FORMATS:
        return jsonify({'error': '不支持的格式'}), 400
    converter = _get_state('converter')
    report_dir = _PROJECT_ROOT
    if converter and hasattr(converter, 'config') and converter.config.report_output_dir:
        report_dir = converter.config.report_output_dir
    pattern = os.path.join(report_dir, f'conversion_report_*.{fmt}')
    files = sorted(glob.glob(pattern), key=os.path.getmtime, reverse=True)
    if not files:
        return jsonify({'error': '未找到报告文件'}), 404
    return send_file(files[0], as_attachment=True, download_name=os.path.basename(files[0]))


@app.route('/api/report/smart-analysis', methods=['POST'])
@require_api_token
@require_csrf
def api_smart_analysis_report() -> Tuple:
    data = request.get_json(silent=True) or {}
    fmt = str(data.get('format', 'txt')).lower()
    if fmt not in _ALLOWED_REPORT_FORMATS:
        return jsonify({'error': f'不支持的格式: {fmt}'}), 400
    converter = _get_state('converter')
    if not converter or not hasattr(converter, 'report_details') or not converter.report_details:
        return jsonify({'error': '暂无转换数据'}), 400
    try:
        converter.export_smart_analysis_report(fmt)
        report_dir = converter.config.report_output_dir or _PROJECT_ROOT
        pattern = os.path.join(report_dir, f'smart_analysis_report_*.{fmt}')
        files = sorted(glob.glob(pattern), key=os.path.getmtime, reverse=True)
        filepath = files[0] if files else ''
        _add_log('success', f'智能分析报告已生成: {filepath}')
        return jsonify({'success': True, 'filepath': filepath})
    except Exception as e:
        _add_log('error', f'生成智能分析报告失败: {e}')
        return jsonify({'error': str(e)}), 500


@app.route('/api/report/performance', methods=['POST'])
@require_api_token
@require_csrf
def api_performance_report() -> Tuple:
    data = request.get_json(silent=True) or {}
    fmt = str(data.get('format', 'txt')).lower()
    if fmt not in _ALLOWED_REPORT_FORMATS:
        return jsonify({'error': f'不支持的格式: {fmt}'}), 400
    converter = _get_state('converter')
    if not converter or not hasattr(converter, 'report_details') or not converter.report_details:
        return jsonify({'error': '暂无转换数据'}), 400
    try:
        converter.export_performance_report(fmt)
        report_dir = converter.config.report_output_dir or _PROJECT_ROOT
        pattern = os.path.join(report_dir, f'performance_report_*.{fmt}')
        files = sorted(glob.glob(pattern), key=os.path.getmtime, reverse=True)
        filepath = files[0] if files else ''
        _add_log('success', f'性能报告已生成: {filepath}')
        return jsonify({'success': True, 'filepath': filepath})
    except Exception as e:
        _add_log('error', f'生成性能报告失败: {e}')
        return jsonify({'error': str(e)}), 500


# ============================================================================
# 断点 API
# ============================================================================

@app.route('/api/checkpoint')
@require_api_token
def api_get_checkpoint() -> Dict:
    converter = _get_state('converter')
    if not converter or not hasattr(converter, 'checkpoint'):
        return jsonify({'error': '转换器未初始化，请先启动一次转换'})
    try:
        cp = converter.checkpoint
        info = {
            'filepath': getattr(cp, 'checkpoint_file', '未知'),
            'completed_count': len(getattr(cp, 'completed', set())),
            'failed_count': len(getattr(cp, 'failed', {})),
            'last_updated': datetime.fromtimestamp(os.path.getmtime(cp.checkpoint_file)).strftime('%Y-%m-%d %H:%M:%S')
                if hasattr(cp, 'checkpoint_file') and os.path.exists(cp.checkpoint_file) else '-',
            'completed_files': [],
        }
        for fp in sorted(getattr(cp, 'completed', set()))[:100]:
            info['completed_files'].append({'filepath': fp, 'status': 'completed'})
        for fp in sorted(getattr(cp, 'failed', {}).keys())[:50]:
            info['completed_files'].append({'filepath': fp, 'status': 'failed'})
        return jsonify({'checkpoint': info})
    except Exception as e:
        return jsonify({'error': f'获取断点失败: {e}'}), 500


@app.route('/api/checkpoint', methods=['DELETE'])
@require_api_token
@require_csrf
def api_reset_checkpoint() -> Dict:
    converter = _get_state('converter')
    if not converter or not hasattr(converter, 'checkpoint'):
        return jsonify({'error': '转换器未初始化'}), 400
    try:
        cp = converter.checkpoint
        if hasattr(cp, 'clear'):
            cp.clear()
        else:
            if hasattr(cp, 'completed'): cp.completed.clear()
            if hasattr(cp, 'failed'): cp.failed.clear()
        _add_log('warning', '断点已重置')
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': f'重置失败: {e}'}), 500


@app.route('/api/retry-failed', methods=['POST'])
@require_api_token
@require_csrf
def api_retry_failed() -> Tuple:
    converter = _get_state('converter')
    if not converter or not hasattr(converter, 'checkpoint'):
        return jsonify({'error': '转换器未初始化'}), 400
    if _get_state('is_running'):
        return jsonify({'error': '转换正在进行中'}), 400
    data = request.get_json(silent=True) or {}
    retry_type = str(data.get('type', 'all'))
    cp = converter.checkpoint
    failed_files = dict(getattr(cp, 'failed', {}))
    if not failed_files:
        return jsonify({'error': '没有失败的文件需要重试'}), 400
    to_retry = []
    for filepath, error_msg in failed_files.items():
        if retry_type == 'all':
            to_retry.append(filepath)
        elif retry_type == 'nfo_missing' and 'nfo' in error_msg.lower():
            to_retry.append(filepath)
        elif retry_type == 'error' and 'nfo' not in error_msg.lower() and 'delete' not in error_msg.lower():
            to_retry.append(filepath)
        elif retry_type == 'delete_failed' and 'delete' in error_msg.lower():
            to_retry.append(filepath)
    if not to_retry:
        return jsonify({'error': f'没有匹配 "{retry_type}" 类型的失败文件'}), 400
    for fp in to_retry:
        cp.failed.pop(fp, None)
        cp.completed.discard(fp)
    if hasattr(cp, 'save'):
        cp.save()
    _add_log('info', f'已标记 {len(to_retry)} 个文件待重试（类型: {retry_type}）')
    return jsonify({'success': True, 'count': len(to_retry), 'type': retry_type})


# ============================================================================
# 备份 API
# ============================================================================

@app.route('/api/backups')
@require_api_token
def api_get_backups() -> Dict:
    converter = _get_state('converter')
    if not converter:
        return jsonify({'files': []})
    backup_dir = getattr(converter.config, 'backup_dir', '.backup')
    files = []
    if os.path.isdir(backup_dir):
        for f in os.listdir(backup_dir):
            fp = os.path.join(backup_dir, f)
            if os.path.isfile(fp):
                stat = os.stat(fp)
                files.append({'name': f, 'path': fp, 'size': stat.st_size,
                              'modified': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')})
    files.sort(key=lambda x: x['modified'], reverse=True)
    return jsonify({'files': files[:200]})


@app.route('/api/backups/delete', methods=['POST'])
@require_api_token
@require_csrf
def api_delete_backup() -> Tuple:
    data = request.get_json(silent=True) or {}
    path = str(data.get('path', ''))
    if not path or not os.path.isfile(path):
        return jsonify({'error': '文件不存在'}), 404
    if not _validate_path(path, allow_absolute=True):
        return jsonify({'error': '路径不安全'}), 403
    try:
        os.remove(path)
        _add_log('info', f'已删除备份: {os.path.basename(path)}')
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': f'删除失败: {e}'}), 500


@app.route('/api/backups/clean', methods=['POST'])
@require_api_token
@require_csrf
def api_clean_backups() -> Dict:
    converter = _get_state('converter')
    if not converter:
        return jsonify({'error': '转换器未初始化'}), 400
    try:
        config = converter.config
        backup_dir = getattr(config, 'backup_dir', '.backup')
        max_count = getattr(config, 'backup_max_count', 5)
        max_age_days = getattr(config, 'backup_max_age_days', 30)
        if not os.path.isdir(backup_dir):
            return jsonify({'success': True, 'deleted': 0})
        deleted = 0
        now = time.time()
        max_age_seconds = max_age_days * 86400
        dir_files: Dict[str, List[str]] = {}
        for f in os.listdir(backup_dir):
            fp = os.path.join(backup_dir, f)
            if not os.path.isfile(fp):
                continue
            try:
                if max_age_days > 0 and (now - os.path.getmtime(fp)) > max_age_seconds:
                    os.remove(fp)
                    deleted += 1
                    continue
            except OSError:
                continue
            dir_files.setdefault('.', []).append(fp)
        if max_count > 0:
            for dir_key, files in dir_files.items():
                files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
                for fp in files[max_count:]:
                    try:
                        os.remove(fp)
                        deleted += 1
                    except OSError:
                        pass
        _add_log('info', f'已清理 {deleted} 个过期备份')
        return jsonify({'success': True, 'deleted': deleted})
    except Exception as e:
        return jsonify({'error': f'清理失败: {e}'}), 500


# ============================================================================
# 配置导入/导出 API
# ============================================================================

@app.route('/api/config/export')
@require_api_token
def api_export_config():
    config = _get_state('config')
    if not config or not is_dataclass(config):
        return jsonify({'error': '无配置可导出'}), 400
    try:
        content = json.dumps(asdict(config), ensure_ascii=False, indent=2)
        return send_file(
            __import__('io').BytesIO(content.encode('utf-8')),
            mimetype='application/json',
            as_attachment=True,
            download_name='nfo_converter_config.json'
        )
    except Exception as e:
        return jsonify({'error': f'导出失败: {e}'}), 500


@app.route('/api/config/import', methods=['POST'])
@require_api_token
@require_csrf
def api_import_config() -> Tuple:
    data = request.get_json(silent=True)
    if not data or not isinstance(data, dict):
        return jsonify({'error': '请求体必须是 JSON 对象'}), 400
    try:
        from nfo_to_vsmeta_converter_complete import Config
        validated, error = _validate_config_data(data)
        if error and not validated:
            return jsonify({'error': error}), 400
        config = Config(**validated)
        _set_state('config', config)
        converter = _get_state('converter')
        if converter:
            converter.config = config
        _add_log('success', '配置已从 JSON 导入')
        return jsonify({'success': True})
    except TypeError as e:
        return jsonify({'error': f'配置参数错误: {e}'}), 400
    except Exception as e:
        return jsonify({'error': f'导入失败: {e}'}), 500


# ============================================================================
# 插件 API
# ============================================================================

@app.route('/api/plugins')
@require_api_token
def api_get_plugins() -> Dict:
    converter = _get_state('converter')
    plugins = []
    if converter and hasattr(converter, 'plugin_manager'):
        plugins = converter.plugin_manager.list_plugins()
    return jsonify({'plugins': plugins})


@app.route('/api/plugins/load', methods=['POST'])
@require_api_token
@require_csrf
def api_load_plugins() -> Tuple:
    data = request.get_json(silent=True)
    if not data or not isinstance(data, dict):
        return jsonify({'error': '请求体不能为空'}), 400
    directory = str(data.get('directory', 'plugins')).strip()
    if not _validate_path(directory, allow_absolute=True):
        return jsonify({'error': '插件目录路径不安全'}), 403
    try:
        from nfo_to_vsmeta_converter_complete import Config, NFOToVSMETAConverter
        converter = _get_state('converter')
        if not converter:
            converter = NFOToVSMETAConverter(Config())
            _set_state('converter', converter)
        count = converter.plugin_manager.load_from_directory(directory)
        _add_log('success', f'已从 {directory} 加载 {count} 个插件')
        return jsonify({'success': True, 'count': count})
    except Exception as e:
        _add_log('error', f'加载插件失败: {e}')
        return jsonify({'error': f'加载插件失败: {e}'}), 500


@app.route('/api/plugins/unload', methods=['POST'])
@require_api_token
@require_csrf
def api_unload_plugin() -> Tuple:
    data = request.get_json(silent=True)
    if not data or not isinstance(data, dict):
        return jsonify({'error': '请求体不能为空'}), 400
    name = str(data.get('name', '')).strip()
    if not name:
        return jsonify({'error': '插件名称不能为空'}), 400
    converter = _get_state('converter')
    if converter and hasattr(converter, 'plugin_manager'):
        converter.plugin_manager.unregister(name)
        _add_log('info', f'已卸载插件: {name}')
        return jsonify({'success': True})
    return jsonify({'error': '转换器未初始化'}), 400


@app.route('/api/plugins/<name>/config')
@require_api_token
def api_get_plugin_config(name: str) -> Dict:
    """获取指定插件的配置"""
    converter = _get_state('converter')
    if not converter or not hasattr(converter, 'plugin_manager'):
        return jsonify({'error': '转换器未初始化'}), 400
    pm = converter.plugin_manager
    plugin = pm.get_plugin(name)
    if not plugin:
        return jsonify({'error': f'插件 {name} 不存在'}), 404
    config = pm.get_plugin_config(name)
    schema = {}
    try:
        schema = plugin.config_schema
    except Exception as e:
        logger.debug(f"获取插件 {name} 的配置 schema 失败: {e}")
    return jsonify({
        'name': name,
        'config': config.get_all() if config else {},
        'schema': schema
    })


@app.route('/api/plugins/<name>/config', methods=['POST'])
@require_api_token
@require_csrf
def api_set_plugin_config(name: str) -> Dict:
    """更新指定插件的配置"""
    data = request.get_json(silent=True)
    if not data or not isinstance(data, dict):
        return jsonify({'error': '请求体不能为空'}), 400
    converter = _get_state('converter')
    if not converter or not hasattr(converter, 'plugin_manager'):
        return jsonify({'error': '转换器未初始化'}), 400
    pm = converter.plugin_manager
    if name not in pm._plugins:
        return jsonify({'error': f'插件 {name} 不存在'}), 404
    success = pm.update_plugin_config(name, data)
    if success:
        _add_log('success', f'已更新插件 {name} 的配置')
        return jsonify({'success': True})
    return jsonify({'error': '更新配置失败'}), 500


@app.route('/api/plugins/<name>/priority', methods=['POST'])
@require_api_token
@require_csrf
def api_set_plugin_priority(name: str) -> Dict:
    """更新插件优先级"""
    data = request.get_json(silent=True)
    if not data or 'priority' not in data:
        return jsonify({'error': '缺少 priority 参数'}), 400
    try:
        priority = int(data['priority'])
        if not 0 <= priority <= 100:
            return jsonify({'error': '优先级范围 0-100'}), 400
    except (ValueError, TypeError):
        return jsonify({'error': 'priority 必须是整数'}), 400
    converter = _get_state('converter')
    if not converter or not hasattr(converter, 'plugin_manager'):
        return jsonify({'error': '转换器未初始化'}), 400
    pm = converter.plugin_manager
    plugin = pm.get_plugin(name)
    if not plugin:
        return jsonify({'error': f'插件 {name} 不存在'}), 404
    try:
        plugin._plugin_priority = priority
        _add_log('info', f'已更新插件 {name} 的优先级为 {priority}')
        return jsonify({'success': True, 'priority': priority})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/plugins/hot-reload', methods=['POST'])
@require_api_token
@require_csrf
def api_toggle_hot_reload() -> Dict:
    """启用/禁用热重载"""
    data = request.get_json(silent=True) or {}
    enabled = bool(data.get('enabled', False))
    converter = _get_state('converter')
    if not converter or not hasattr(converter, 'plugin_manager'):
        return jsonify({'error': '转换器未初始化'}), 400
    pm = converter.plugin_manager
    if enabled:
        config = _get_state('config')
        plugin_dir = config.plugin_dir if config and hasattr(config, 'plugin_dir') else 'plugins'
        success = pm.enable_hot_reload(plugin_dir, config)
        if success:
            _add_log('success', f'已启用插件热重载，监控目录: {plugin_dir}')
        else:
            _add_log('warning', '启用热重载失败，可能缺少 watchdog 库')
        return jsonify({'enabled': success})
    else:
        pm.disable_hot_reload()
        _add_log('info', '已禁用插件热重载')
        return jsonify({'enabled': False})


@app.route('/api/plugins/<name>/reload', methods=['POST'])
@require_api_token
@require_csrf
def api_reload_plugin(name: str) -> Dict:
    """手动重载指定插件"""
    converter = _get_state('converter')
    if not converter or not hasattr(converter, 'plugin_manager'):
        return jsonify({'error': '转换器未初始化'}), 400
    pm = converter.plugin_manager
    success = pm.reload_plugin(name)
    if success:
        _add_log('success', f'已手动重载插件: {name}')
        return jsonify({'success': True})
    return jsonify({'error': f'重载插件 {name} 失败'}), 500


@app.route('/api/plugins/create', methods=['POST'])
@require_api_token
@require_csrf
def api_create_plugin() -> Dict:
    """创建插件模板"""
    data = request.get_json(silent=True) or {}
    name = str(data.get('name', '')).strip()
    plugin_type = str(data.get('type', 'enhancer')).strip()
    if not name:
        return jsonify({'error': '插件名称不能为空'}), 400
    if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_-]*$', name):
        return jsonify({'error': '插件名称只能包含字母、数字、下划线和连字符，且不能以数字开头'}), 400
    allowed_types = ('enhancer', 'parser', 'generator', 'filter', 'lifecycle')
    if plugin_type not in allowed_types:
        return jsonify({'error': f'不支持的插件类型，可选: {", ".join(allowed_types)}'}), 400
    try:
        from nfo_to_vsmeta_converter_complete import create_plugin_template
        path = create_plugin_template(
            name=name,
            plugin_type=plugin_type,
            author=str(data.get('author', 'Anonymous')),
            version=str(data.get('version', '1.0.0')),
            description=str(data.get('description', '')),
            priority=int(data.get('priority', 50))
        )
        _add_log('success', f'已创建插件模板: {path}')
        return jsonify({'success': True, 'path': path})
    except Exception as e:
        _add_log('error', f'创建插件模板失败: {e}')
        return jsonify({'error': str(e)}), 500


# ============================================================================
# 启动
# ============================================================================

def main() -> None:
    if not HAS_FLASK:
        print("错误: 请先安装 Flask: pip install flask")
        sys.exit(1)
    parser = argparse.ArgumentParser(description='NFO to VSMETA 转换器 - Web UI v4.0')
    parser.add_argument('--host', default='127.0.0.1', help='监听地址')
    parser.add_argument('--port', type=int, default=5000, help='监听端口')
    parser.add_argument('--debug', action='store_true', help='调试模式')
    parser.add_argument('--token', default='', help='API 认证 Token')
    args = parser.parse_args()

    if args.token:
        _state['api_token'] = args.token
        print("⚠️  API 认证已启用")
    if args.host == '0.0.0.0' and not args.token:
        print("⚠️  警告: 绑定 0.0.0.0 且未设置 API Token，建议使用 --token")

    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s', datefmt='%H:%M:%S'))
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG if args.debug else logging.INFO)

    print(f"""
╔══════════════════════════════════════════╗
║   NFO to VSMETA 转换器 - Web UI v4.0      ║
╠══════════════════════════════════════════╣
║   地址: http://{args.host}:{args.port:<27s}  ║
║   按 Ctrl+C 停止                          ║
╚══════════════════════════════════════════╝
    """)
    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == '__main__':
    main()
