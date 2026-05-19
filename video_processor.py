"""
视频处理模块

提供视频元数据提取、缩略图生成、视频分析等功能

依赖库：
- opencv-python (opencv): 视频处理
- pillow (PIL): 图片处理

支持：
- 视频元数据提取（分辨率、帧率、时长等）
- 缩略图生成（指定时间点或自动选择）
- 视频帧提取
- 视频质量分析
"""

import logging
import os
import tempfile
from typing import Any, Dict, List, Optional, Tuple, Union
from pathlib import Path
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# 检查依赖库
try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    logger.warning("opencv 未安装，视频处理功能不可用。请安装：pip install opencv-python")

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    logger.warning("Pillow 未安装，图片处理功能不可用。请安装：pip install Pillow")


@dataclass
class VideoMetadata:
    """视频元数据"""
    file_path: str
    filename: str
    duration: float  # 秒
    width: int
    height: int
    fps: float
    frame_count: int
    codec: str
    bitrate: Optional[int] = None
    file_size: Optional[int] = None
    format_name: Optional[str] = None

    @property
    def resolution(self) -> str:
        """获取分辨率字符串"""
        return f"{self.width}x{self.height}"

    @property
    def aspect_ratio(self) -> float:
        """获取宽高比"""
        if self.height > 0:
            return self.width / self.height
        return 0.0

    @property
    def duration_str(self) -> str:
        """获取时长字符串（HH:MM:SS）"""
        hours = int(self.duration // 3600)
        minutes = int((self.duration % 3600) // 60)
        seconds = int(self.duration % 60)
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        return f"{minutes:02d}:{seconds:02d}"


class VideoProcessor:
    """视频处理器"""

    SUPPORTED_FORMATS = [
        '.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv',
        '.webm', '.m4v', '.mpg', '.mpeg', '.3gp'
    ]

    def __init__(self):
        """初始化视频处理器"""
        self._check_dependencies()

    def _check_dependencies(self):
        """检查依赖是否满足"""
        if not CV2_AVAILABLE:
            raise RuntimeError(
                "opencv-python 未安装，无法使用视频处理功能。\n"
                "请运行: pip install opencv-python"
            )

    def is_video_file(self, file_path: str) -> bool:
        """
        检查文件是否为支持的视频格式

        Args:
            file_path: 文件路径

        Returns:
            是否为视频文件
        """
        ext = Path(file_path).suffix.lower()
        return ext in self.SUPPORTED_FORMATS

    def extract_metadata(self, video_path: str) -> VideoMetadata:
        """
        提取视频元数据

        Args:
            video_path: 视频文件路径

        Returns:
            视频元数据对象

        Raises:
            FileNotFoundError: 视频文件不存在
            RuntimeError: 视频处理失败
        """
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"视频文件不存在: {video_path}")

        cap = cv2.VideoCapture(video_path)

        if not cap.isOpened():
            raise RuntimeError(f"无法打开视频文件: {video_path}")

        try:
            # 获取基本信息
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            duration = frame_count / fps if fps > 0 else 0

            # 获取编解码器信息
            fourcc_int = int(cap.get(cv2.CAP_PROP_FOURCC))
            codec = "".join([chr((fourcc_int >> 8 * i) & 0xFF) for i in range(4)])

            # 获取文件大小
            file_size = os.path.getsize(video_path) if os.path.exists(video_path) else None

            return VideoMetadata(
                file_path=video_path,
                filename=os.path.basename(video_path),
                duration=duration,
                width=width,
                height=height,
                fps=fps,
                frame_count=frame_count,
                codec=codec,
                bitrate=None,
                file_size=file_size,
                format_name=Path(video_path).suffix.lower()
            )

        finally:
            cap.release()

    def extract_thumbnail(
        self,
        video_path: str,
        output_path: Optional[str] = None,
        timestamp: Optional[float] = None,
        width: Optional[int] = None,
        quality: int = 85
    ) -> Optional[str]:
        """
        从视频中提取缩略图

        Args:
            video_path: 视频文件路径
            output_path: 输出图片路径（可选，默认生成临时文件）
            timestamp: 提取时间点（秒），None 则自动选择
            width: 输出图片宽度（可选，保持比例）
            quality: JPEG 质量 (1-100)

        Returns:
            缩略图文件路径

        Raises:
            RuntimeError: 提取失败
        """
        cap = cv2.VideoCapture(video_path)

        if not cap.isOpened():
            raise RuntimeError(f"无法打开视频文件: {video_path}")

        try:
            # 获取视频信息
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            duration = frame_count / fps if fps > 0 else 0

            # 确定提取的时间点
            if timestamp is None:
                # 自动选择：通常选择 1/4 位置
                timestamp = duration * 0.25

            # 确保时间在有效范围内
            timestamp = max(0, min(timestamp, duration - 0.1))

            # 跳转到指定时间
            frame_pos = int(timestamp * fps)
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_pos)

            # 读取帧
            ret, frame = cap.read()

            if not ret or frame is None:
                logger.warning(f"无法读取视频帧: {video_path} at {timestamp}s")
                return None

            # 处理图片尺寸
            if width is not None:
                h, w = frame.shape[:2]
                new_height = int(h * (width / w))
                frame = cv2.resize(frame, (width, new_height), interpolation=cv2.INTER_AREA)

            # 确定输出路径
            if output_path is None:
                fd, output_path = tempfile.mkstemp(suffix='.jpg', prefix='thumb_')
                os.close(fd)

            # 确保输出目录存在
            os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)

            # 保存图片
            if PIL_AVAILABLE:
                # 使用 Pillow 保存（更好的质量控制）
                img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                img.save(output_path, 'JPEG', quality=quality, optimize=True)
            else:
                # 使用 OpenCV 保存
                cv2.imwrite(output_path, frame, [cv2.IMWRITE_JPEG_QUALITY, quality])

            logger.info(f"缩略图已生成: {output_path}")
            return output_path

        finally:
            cap.release()

    def extract_multiple_thumbnails(
        self,
        video_path: str,
        output_dir: str,
        count: int = 5,
        width: Optional[int] = None,
        quality: int = 85
    ) -> List[str]:
        """
        从视频中提取多个缩略图

        Args:
            video_path: 视频文件路径
            output_dir: 输出目录
            count: 缩略图数量
            width: 输出图片宽度
            quality: JPEG 质量

        Returns:
            缩略图文件路径列表
        """
        # 获取视频时长
        metadata = self.extract_metadata(video_path)
        duration = metadata.duration

        # 生成时间点列表（均匀分布）
        timestamps = [
            duration * (i + 1) / (count + 1)
            for i in range(count)
        ]

        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)

        # 提取缩略图
        thumbnails = []
        video_name = Path(video_path).stem

        for i, timestamp in enumerate(timestamps):
            output_path = os.path.join(
                output_dir,
                f"{video_name}_thumb_{i+1:02d}.jpg"
            )

            try:
                result = self.extract_thumbnail(
                    video_path,
                    output_path,
                    timestamp,
                    width,
                    quality
                )
                if result:
                    thumbnails.append(result)
            except Exception as e:
                logger.error(f"提取缩略图失败: {e}")

        return thumbnails

    def extract_keyframes(
        self,
        video_path: str,
        output_dir: str,
        threshold: float = 30.0
    ) -> List[str]:
        """
        提取关键帧（场景变化较大的帧）

        Args:
            video_path: 视频文件路径
            output_dir: 输出目录
            threshold: 场景变化阈值

        Returns:
            关键帧文件路径列表
        """
        cap = cv2.VideoCapture(video_path)

        if not cap.isOpened():
            raise RuntimeError(f"无法打开视频文件: {video_path}")

        try:
            os.makedirs(output_dir, exist_ok=True)

            # 读取第一帧作为参考
            ret, prev_frame = cap.read()
            if not ret:
                return []

            prev_gray = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)
            prev_gray = cv2.GaussianBlur(prev_gray, (21, 21), 0)

            keyframes = []
            frame_idx = 0
            keyframe_idx = 0

            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                # 转换为灰度图
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                gray = cv2.GaussianBlur(gray, (21, 21), 0)

                # 计算与上一帧的差异
                delta = cv2.absdiff(prev_gray, gray)
                thresh = cv2.threshold(delta, 25, 255, cv2.THRESH_BINARY)[1]
                diff = cv2.sumElems(thresh)[0]

                # 如果差异超过阈值，认为是关键帧
                if diff > threshold:
                    output_path = os.path.join(
                        output_dir,
                        f"keyframe_{keyframe_idx:04d}.jpg"
                    )

                    if PIL_AVAILABLE:
                        img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                        img.save(output_path, 'JPEG', quality=90)
                    else:
                        cv2.imwrite(output_path, frame)

                    keyframes.append(output_path)
                    keyframe_idx += 1

                prev_gray = gray
                frame_idx += 1

            return keyframes

        finally:
            cap.release()

    def get_video_info(self, video_path: str) -> Dict[str, Any]:
        """
        获取视频详细信息

        Args:
            video_path: 视频文件路径

        Returns:
            视频信息字典
        """
        metadata = self.extract_metadata(video_path)

        return {
            "文件名": metadata.filename,
            "文件路径": metadata.file_path,
            "文件大小": self._format_file_size(metadata.file_size) if metadata.file_size else "未知",
            "格式": metadata.format_name,
            "时长": metadata.duration_str,
            "时长(秒)": round(metadata.duration, 2),
            "分辨率": metadata.resolution,
            "宽高比": f"{metadata.aspect_ratio:.2f}",
            "帧率": f"{metadata.fps:.2f} fps",
            "总帧数": metadata.frame_count,
            "编码": metadata.codec,
        }

    @staticmethod
    def _format_file_size(size: int) -> str:
        """格式化文件大小"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.2f} {unit}"
            size /= 1024.0
        return f"{size:.2f} TB"

    def validate_video(self, video_path: str) -> Tuple[bool, Optional[str]]:
        """
        验证视频文件是否可读

        Args:
            video_path: 视频文件路径

        Returns:
            (是否有效, 错误信息)
        """
        if not os.path.exists(video_path):
            return False, "文件不存在"

        if not self.is_video_file(video_path):
            return False, f"不支持的视频格式: {Path(video_path).suffix}"

        try:
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                return False, "无法打开视频文件"
            if cap.get(cv2.CAP_PROP_FRAME_COUNT) == 0:
                return False, "视频文件为空或损坏"
            cap.release()
            return True, None
        except Exception as e:
            return False, str(e)


# 快捷函数
def get_video_metadata(video_path: str) -> VideoMetadata:
    """获取视频元数据"""
    return VideoProcessor().extract_metadata(video_path)


def generate_thumbnail(
    video_path: str,
    output_path: Optional[str] = None,
    timestamp: Optional[float] = None,
    width: Optional[int] = None
) -> Optional[str]:
    """生成视频缩略图"""
    return VideoProcessor().extract_thumbnail(video_path, output_path, timestamp, width)


def get_video_info(video_path: str) -> Dict[str, Any]:
    """获取视频详细信息"""
    return VideoProcessor().get_video_info(video_path)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    print("=" * 60)
    print("视频处理模块测试")
    print("=" * 60)

    # 检查依赖
    if not CV2_AVAILABLE:
        print("❌ opencv-python 未安装")
        print("   安装命令：pip install opencv-python")
    else:
        print("✅ opencv-python 已安装")

    if not PIL_AVAILABLE:
        print("⚠️  Pillow 未安装（可选）")
        print("   安装命令：pip install Pillow")
    else:
        print("✅ Pillow 已安装")

    # 列出支持的格式
    print("\n支持的视频格式:")
    processor = VideoProcessor()
    print(f"  {', '.join(processor.SUPPORTED_FORMATS)}")

    # 示例用法
    print("\n示例用法:")
    print("  # 获取视频元数据")
    print("  metadata = get_video_metadata('video.mp4')")
    print("  print(f'时长: {metadata.duration_str}')")
    print("")
    print("  # 生成缩略图")
    print("  thumb = generate_thumbnail('video.mp4', 'thumb.jpg')")
    print("")
    print("  # 获取视频信息")
    print("  info = get_video_info('video.mp4')")
    print("  for key, value in info.items():")
    print("      print(f'{key}: {value}')")
