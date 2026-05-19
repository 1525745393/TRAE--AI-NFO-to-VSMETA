"""
视频处理功能测试
"""

import pytest
import tempfile
import os
from pathlib import Path

try:
    import cv2
    import PIL
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

from video_processor import (
    VideoProcessor,
    VideoMetadata,
    get_video_metadata,
    generate_thumbnail,
    get_video_info,
)


class TestVideoProcessor:
    """视频处理器测试"""

    def test_initialization(self):
        """测试初始化"""
        if not CV2_AVAILABLE:
            pytest.skip("opencv 未安装")

        processor = VideoProcessor()
        assert processor is not None

    def test_supported_formats(self):
        """测试支持的格式"""
        processor = VideoProcessor()
        assert '.mp4' in processor.SUPPORTED_FORMATS
        assert '.avi' in processor.SUPPORTED_FORMATS
        assert '.mkv' in processor.SUPPORTED_FORMATS

    def test_is_video_file(self):
        """测试视频文件识别"""
        processor = VideoProcessor()
        assert processor.is_video_file('test.mp4')
        assert processor.is_video_file('test.avi')
        assert processor.is_video_file('test.mkv')
        assert not processor.is_video_file('test.txt')
        assert not processor.is_video_file('test.jpg')

    @pytest.mark.skipif(not CV2_AVAILABLE, reason="opencv 未安装")
    def test_validate_video_nonexistent(self):
        """测试验证不存在的文件"""
        processor = VideoProcessor()
        valid, error = processor.validate_video('/nonexistent/video.mp4')
        assert not valid
        assert error == "文件不存在"

    @pytest.mark.skipif(not CV2_AVAILABLE, reason="opencv 未安装")
    def test_validate_video_invalid_format(self):
        """测试验证不支持的格式"""
        processor = VideoProcessor()

        # 创建临时文本文件
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as f:
            f.write(b'test content')
            temp_file = f.name

        try:
            valid, error = processor.validate_video(temp_file)
            assert not valid
            assert "不支持的视频格式" in error
        finally:
            os.unlink(temp_file)

    def test_format_file_size(self):
        """测试文件大小格式化"""
        assert "B" in VideoProcessor._format_file_size(100)
        assert "KB" in VideoProcessor._format_file_size(1024)
        assert "MB" in VideoProcessor._format_file_size(1024 * 1024)
        assert "GB" in VideoProcessor._format_file_size(1024 * 1024 * 1024)


@pytest.mark.skipif(not CV2_AVAILABLE, reason="opencv 未安装")
class TestVideoMetadata:
    """视频元数据测试"""

    def test_metadata_properties(self):
        """测试元数据属性"""
        metadata = VideoMetadata(
            file_path="/path/to/video.mp4",
            filename="video.mp4",
            duration=3661.5,  # 1小时1分1.5秒
            width=1920,
            height=1080,
            fps=24.0,
            frame_count=87876,
            codec="avc1"
        )

        assert metadata.resolution == "1920x1080"
        assert metadata.aspect_ratio == pytest.approx(1.778, rel=0.01)
        assert metadata.duration_str == "01:01:01"


class TestQuickFunctions:
    """快捷函数测试"""

    def test_get_video_metadata_invalid(self):
        """测试获取不存在的视频元数据"""
        with pytest.raises(FileNotFoundError):
            get_video_metadata('/nonexistent/video.mp4')

    def test_generate_thumbnail_invalid(self):
        """测试生成不存在的视频缩略图"""
        with pytest.raises(RuntimeError):
            generate_thumbnail('/nonexistent/video.mp4')

    def test_get_video_info_invalid(self):
        """测试获取不存在的视频信息"""
        with pytest.raises(FileNotFoundError):
            get_video_info('/nonexistent/video.mp4')


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
