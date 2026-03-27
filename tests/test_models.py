"""Tests for img2vid data models."""

import pytest

from src.models import (
    Resolution,
    FrameRange,
    TimeRange,
    OutputSettings,
    ConversionConfig,
    VideoCodec,
    ContainerFormat,
    PixelFormat,
)


class TestResolution:
    """Tests for Resolution dataclass."""

    def test_basic_creation(self):
        res = Resolution(1920, 1080)
        assert res.width == 1920
        assert res.height == 1080

    def test_string_representation(self):
        res = Resolution(1920, 1080)
        assert str(res) == "1920x1080"

    def test_aspect_ratio(self):
        res_16_9 = Resolution(1920, 1080)
        assert abs(res_16_9.aspect_ratio - 1.777777) < 0.001
        
        res_4_3 = Resolution(1440, 1080)
        assert abs(res_4_3.aspect_ratio - 1.333333) < 0.001

    def test_from_preset_hd(self):
        res = Resolution.from_preset("HD")
        assert res.width == 1280
        assert res.height == 720

    def test_from_preset_fhd(self):
        res = Resolution.from_preset("FHD")
        assert res.width == 1920
        assert res.height == 1080

    def test_from_preset_uhd(self):
        res = Resolution.from_preset("UHD")
        assert res.width == 3840
        assert res.height == 2160

    def test_from_preset_4k(self):
        res = Resolution.from_preset("4K")
        assert res.width == 4096
        assert res.height == 2160

    def test_from_preset_invalid(self):
        with pytest.raises(ValueError):
            Resolution.from_preset("INVALID")


class TestFrameRange:
    """Tests for FrameRange dataclass."""

    def test_default_values(self):
        fr = FrameRange()
        assert fr.start == 1
        assert fr.end is None

    def test_custom_values(self):
        fr = FrameRange(start=10, end=100)
        assert fr.start == 10
        assert fr.end == 100

    def test_validate_valid_range(self):
        fr = FrameRange(start=1, end=100)
        assert fr.validate(100) is True
        assert fr.validate(200) is True

    def test_validate_start_too_low(self):
        fr = FrameRange(start=0, end=100)
        assert fr.validate(100) is False

    def test_validate_end_before_start(self):
        fr = FrameRange(start=100, end=50)
        assert fr.validate(100) is False

    def test_validate_end_exceeds_total(self):
        fr = FrameRange(start=1, end=200)
        assert fr.validate(100) is False

    def test_count_with_end(self):
        fr = FrameRange(start=1, end=100)
        assert fr.count() == 100

    def test_count_with_offset_start(self):
        fr = FrameRange(start=10, end=20)
        assert fr.count() == 11

    def test_count_without_end(self):
        fr = FrameRange(start=1)
        assert fr.count() == 0


class TestTimeRange:
    """Tests for TimeRange dataclass."""

    def test_default_values(self):
        tr = TimeRange()
        assert tr.start_seconds == 0.0
        assert tr.duration_seconds is None

    def test_to_ffmpeg_args_empty(self):
        tr = TimeRange()
        args = tr.to_ffmpeg_args()
        assert args == []

    def test_to_ffmpeg_args_with_start(self):
        tr = TimeRange(start_seconds=5.5)
        args = tr.to_ffmpeg_args()
        assert args == ["-ss", "5.500"]

    def test_to_ffmpeg_args_with_duration(self):
        tr = TimeRange(duration_seconds=10.0)
        args = tr.to_ffmpeg_args()
        assert args == ["-t", "10.000"]

    def test_to_ffmpeg_args_with_both(self):
        tr = TimeRange(start_seconds=5.0, duration_seconds=10.0)
        args = tr.to_ffmpeg_args()
        assert args == ["-ss", "5.000", "-t", "10.000"]


class TestOutputSettings:
    """Tests for OutputSettings dataclass."""

    def test_default_values(self):
        settings = OutputSettings()
        assert settings.codec == VideoCodec.H264
        assert settings.format == ContainerFormat.MP4
        assert settings.pixel_format == PixelFormat.YUV420P
        assert settings.crf == 23
        assert settings.preset == "medium"

    def test_to_ffmpeg_args_h264(self):
        settings = OutputSettings(codec=VideoCodec.H264, crf=18)
        args = settings.to_ffmpeg_args()
        assert "-c:v" in args
        assert "libx264" in args
        assert "-crf" in args
        assert "18" in args

    def test_to_ffmpeg_args_prores(self):
        settings = OutputSettings(codec=VideoCodec.PRORES)
        args = settings.to_ffmpeg_args()
        assert "-profile:v" in args
        assert "3" in args
        assert "-crf" not in args  # ProRes doesn't use CRF


class TestConversionConfig:
    """Tests for ConversionConfig dataclass."""

    def test_default_values(self):
        config = ConversionConfig(
            input_directory="/test/input",
            output_path="/test/output.mp4",
            resolution=Resolution(1920, 1080),
        )
        assert config.fps == 24.0
        assert config.frame_range is None
        assert config.output_settings.codec == VideoCodec.H264

    def test_validate_valid_config(self):
        config = ConversionConfig(
            input_directory="/test/input",
            output_path="/test/output.mp4",
            resolution=Resolution(1920, 1080),
            fps=24.0,
        )
        errors = config.validate()
        assert errors == []

    def test_validate_invalid_fps(self):
        config = ConversionConfig(
            input_directory="/test/input",
            output_path="/test/output.mp4",
            resolution=Resolution(1920, 1080),
            fps=-5,
        )
        errors = config.validate()
        assert "FPS must be positive" in errors

    def test_validate_invalid_resolution(self):
        config = ConversionConfig(
            input_directory="/test/input",
            output_path="/test/output.mp4",
            resolution=Resolution(0, 0),
        )
        errors = config.validate()
        assert "Resolution dimensions must be positive" in errors

    def test_to_ffmpeg_args_basic(self):
        config = ConversionConfig(
            input_directory="/test/input",
            output_path="/test/output.mp4",
            resolution=Resolution(1920, 1080),
            fps=30,
        )
        args = config.to_ffmpeg_args()
        assert "-framerate" in args
        assert "30" in args
        assert "-i" in args
        assert "/test/input" in args
        assert "-vf" in args
        assert "scale=1920:1080" in args

    def test_to_ffmpeg_args_with_frame_range(self):
        config = ConversionConfig(
            input_directory="/test/input",
            output_path="/test/output.mp4",
            resolution=Resolution(1920, 1080),
            fps=24,
            frame_range=FrameRange(start=10, end=100),
        )
        args = config.to_ffmpeg_args()
        assert "-start_number" in args
        assert "10" in args
