"""Data models for img2vid configuration and settings."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class VideoCodec(str, Enum):
    """Supported video codecs for output."""
    H264 = "libx264"
    H265 = "libx265"
    PRORES = "prores_ks"
    VP9 = "libvpx-vp9"
    RAW = "rawvideo"


class ContainerFormat(str, Enum):
    """Supported container formats."""
    MP4 = "mp4"
    MKV = "mkv"
    MOV = "mov"
    WEBM = "webm"
    AVI = "avi"


class PixelFormat(str, Enum):
    """Supported pixel formats."""
    YUV420P = "yuv420p"
    YUV422P = "yuv422p"
    YUV444P = "yuv444p"
    RGB24 = "rgb24"
    RGBA = "rgba"


@dataclass
class Resolution:
    """Video resolution settings."""
    width: int
    height: int

    @property
    def aspect_ratio(self) -> float:
        """Calculate aspect ratio."""
        return self.width / self.height if self.height > 0 else 0.0

    def __str__(self) -> str:
        return f"{self.width}x{self.height}"

    @classmethod
    def from_preset(cls, preset: str) -> "Resolution":
        """Create resolution from common preset."""
        presets = {
            "HD": cls(1280, 720),
            "FHD": cls(1920, 1080),
            "QHD": cls(2560, 1440),
            "UHD": cls(3840, 2160),
            "4K": cls(4096, 2160),
            "SD": cls(720, 480),
        }
        if preset not in presets:
            raise ValueError(f"Unknown preset: {preset}")
        return presets[preset]


@dataclass
class FrameRange:
    """Frame range for trimming input sequence."""
    start: int = 1
    end: Optional[int] = None

    def validate(self, total_frames: int) -> bool:
        """Validate frame range against total frames."""
        if self.start < 1:
            return False
        if self.end is not None and self.end < self.start:
            return False
        if self.end is not None and self.end > total_frames:
            return False
        return True

    def count(self) -> int:
        """Get number of frames in range."""
        if self.end is None:
            return 0
        return self.end - self.start + 1


@dataclass
class TimeRange:
    """Time range for trimming (alternative to frame range)."""
    start_seconds: float = 0.0
    duration_seconds: Optional[float] = None

    def to_ffmpeg_args(self) -> list[str]:
        """Convert to FFmpeg arguments."""
        args = []
        if self.start_seconds > 0:
            args.extend(["-ss", f"{self.start_seconds:.3f}"])
        if self.duration_seconds is not None:
            args.extend(["-t", f"{self.duration_seconds:.3f}"])
        return args


@dataclass
class OutputSettings:
    """Output video settings."""
    codec: VideoCodec = VideoCodec.H264
    format: ContainerFormat = ContainerFormat.MP4
    pixel_format: PixelFormat = PixelFormat.YUV420P
    crf: int = 23  # Constant Rate Factor (lower = better quality)
    preset: str = "medium"  # Encoding preset (ultrafast to veryslow)
    audio: bool = False

    def to_ffmpeg_args(self) -> list[str]:
        """Convert to FFmpeg arguments."""
        args = [
            "-c:v", self.codec.value,
            "-pix_fmt", self.pixel_format.value,
            "-preset", self.preset,
        ]
        
        # CRF not applicable for all codecs
        if self.codec in (VideoCodec.H264, VideoCodec.H265, VideoCodec.VP9):
            args.extend(["-crf", str(self.crf)])
        
        # ProRes specific settings
        if self.codec == VideoCodec.PRORES:
            args.extend(["-profile:v", "3"])  # ProRes 422 HQ
        
        return args


@dataclass
class ConversionConfig:
    """Complete conversion configuration."""
    input_directory: str
    output_path: str
    resolution: Resolution
    fps: float = 24.0
    frame_range: Optional[FrameRange] = None
    time_range: Optional[TimeRange] = None
    output_settings: OutputSettings = field(default_factory=OutputSettings)
    pattern: str = "*.png"  # File pattern for image sequence

    def validate(self) -> list[str]:
        """Validate configuration and return list of errors."""
        errors = []
        
        if self.fps <= 0:
            errors.append("FPS must be positive")
        
        if self.resolution.width <= 0 or self.resolution.height <= 0:
            errors.append("Resolution dimensions must be positive")
        
        if self.frame_range and not self.frame_range.validate(999999):
            errors.append("Invalid frame range")
        
        if self.time_range and self.time_range.start_seconds < 0:
            errors.append("Time range start cannot be negative")
        
        return errors

    def to_ffmpeg_args(self) -> list[str]:
        """Convert full config to FFmpeg arguments."""
        args = ["-framerate", str(self.fps)]
        
        # Add frame range if specified
        if self.frame_range and self.frame_range.start > 1:
            args.extend(["-start_number", str(self.frame_range.start)])
        
        # Add time range args
        if self.time_range:
            args.extend(self.time_range.to_ffmpeg_args())
        
        # Add input pattern
        args.extend(["-i", str(self.input_directory)])
        
        # Add scale filter for resolution
        args.extend([
            "-vf", f"scale={self.resolution.width}:{self.resolution.height}"
        ])
        
        # Add output settings
        args.extend(self.output_settings.to_ffmpeg_args())
        
        # Add output path
        args.append(str(self.output_path))
        
        return args
