"""Tests for img2vid utility functions."""

import pytest
from pathlib import Path
import tempfile
import os

from src.utils import (
    detect_sequence_pattern,
    validate_ffmpeg_installed,
    format_duration,
    format_filesize,
    estimate_output_size,
)


class TestDetectSequencePattern:
    """Tests for sequence pattern detection."""

    def test_empty_directory(self):
        """Test with empty directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = detect_sequence_pattern(tmpdir)
            assert result is None

    def test_nonexistent_directory(self):
        """Test with nonexistent directory."""
        result = detect_sequence_pattern("/nonexistent/path/12345")
        assert result is None

    def test_single_sequence(self):
        """Test detecting a single image sequence."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test files
            for i in range(1, 11):
                Path(tmpdir, f"frame_{i:04d}.png").touch()
            
            result = detect_sequence_pattern(tmpdir)
            assert result is not None
            assert result['count'] == 10
            assert result['start'] == 1
            assert result['end'] == 10
            assert result['prefix'] == "frame_"
            assert result['suffix'] == ".png"
            assert result['padding'] == 4

    def test_multiple_sequences(self):
        """Test with multiple sequences - should return largest."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create two sequences
            for i in range(1, 6):
                Path(tmpdir, f"img_{i:03d}.png").touch()
            for i in range(1, 21):
                Path(tmpdir, f"frame_{i:04d}.exr").touch()
            
            result = detect_sequence_pattern(tmpdir)
            assert result is not None
            assert result['count'] == 20  # Should detect the larger sequence
            assert result['suffix'] == ".exr"

    def test_mixed_extensions(self):
        """Test with mixed image extensions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "frame_0001.png").touch()
            Path(tmpdir, "frame_0002.jpg").touch()
            Path(tmpdir, "frame_0003.exr").touch()
            
            result = detect_sequence_pattern(tmpdir)
            # Should still detect as a sequence
            assert result is not None


class TestFormatDuration:
    """Tests for duration formatting."""

    def test_seconds_only(self):
        assert format_duration(5.5) == "5.500s"
        assert format_duration(59.999) == "59.999s"

    def test_minutes_and_seconds(self):
        assert format_duration(65.5) == "01:05.500"
        assert format_duration(125.0) == "02:05.000"

    def test_hours_minutes_seconds(self):
        assert format_duration(3665.5) == "01:01:05.500"
        assert format_duration(7325.0) == "02:02:05.000"

    def test_zero(self):
        assert format_duration(0.0) == "0.000s"


class TestFormatFilesize:
    """Tests for file size formatting."""

    def test_kilobytes(self):
        assert format_filesize(0.5) == "512.00 KB"
        assert format_filesize(0.001) == "1.02 KB"

    def test_megabytes(self):
        assert format_filesize(1.0) == "1.00 MB"
        assert format_filesize(100.5) == "100.50 MB"

    def test_gigabytes(self):
        assert format_filesize(1024.0) == "1.00 GB"
        assert format_filesize(2048.5) == "2.00 GB"


class TestEstimateOutputSize:
    """Tests for output size estimation."""

    def test_1080p_h264(self):
        # 10 seconds of 1080p H.264
        size = estimate_output_size(1920, 1080, 24, 10, 'libx264', 23)
        assert size > 0  # Should be positive
        assert size < 1000  # Should be reasonable (< 1GB for 10s)

    def test_4k_larger_than_1080p(self):
        # 4K should be larger than 1080p for same duration
        size_1080p = estimate_output_size(1920, 1080, 24, 10, 'libx264', 23)
        size_4k = estimate_output_size(3840, 2160, 24, 10, 'libx264', 23)
        assert size_4k > size_1080p

    def test_prores_larger_than_h264(self):
        # ProRes should be much larger than H.264
        size_h264 = estimate_output_size(1920, 1080, 24, 10, 'libx264', 23)
        size_prores = estimate_output_size(1920, 1080, 24, 10, 'prores_ks', 23)
        assert size_prores > size_h264


class TestValidateFFmpeg:
    """Tests for FFmpeg validation."""

    def test_returns_boolean(self):
        result = validate_ffmpeg_installed()
        assert isinstance(result, bool)

    # Note: Actual FFmpeg installation test depends on environment
