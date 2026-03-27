"""Utility functions for img2vid."""

import os
import re
from pathlib import Path
from typing import Optional


def detect_sequence_pattern(directory: str) -> Optional[dict]:
    """
    Detect image sequence pattern in a directory.
    
    Returns information about the detected sequence:
    - prefix: Text before the number
    - suffix: File extension
    - start: First frame number
    - end: Last frame number
    - padding: Number of digits in frame numbers
    - pattern: Glob pattern for the sequence
    - files: List of files sorted by name
    """
    dir_path = Path(directory)
    if not dir_path.exists() or not dir_path.is_dir():
        return None

    # Common image extensions
    image_extensions = {'.png', '.jpg', '.jpeg', '.exr', '.tiff', '.tif', '.bmp', '.webp'}
    
    # Collect all image files and sort by name
    images = []
    for f in dir_path.iterdir():
        if f.is_file() and f.suffix.lower() in image_extensions:
            images.append(f.name)
    
    # Sort files by name (natural sort)
    images = sorted(images, key=lambda x: [int(c) if c.isdigit() else c.lower() 
                                            for c in re.split(r'(\d+)', x)])
    
    if not images:
        return None
    
    # Pattern to match numbered sequences
    sequence_pattern = re.compile(r'^(.*?)(\d+)(\.[a-zA-Z0-9]+)$')
    
    # Group images by prefix and extension
    sequences: dict[tuple[str, str], list[int]] = {}
    
    for img_name in images:
        match = sequence_pattern.match(img_name)
        if match:
            prefix = match.group(1)
            number = int(match.group(2))
            suffix = match.group(3)
            key = (prefix, suffix)
            if key not in sequences:
                sequences[key] = []
            sequences[key].append(number)
    
    if not sequences:
        ext = images[0].split('.')[-1]
        return {
            'prefix': '',
            'suffix': f'.{ext}',
            'start': 1,
            'end': len(images),
            'padding': 1,
            'pattern': f'*.{ext}',
            'count': len(images),
            'files': images,
        }
    
    # Find the largest sequence
    best_key = max(sequences.keys(), key=lambda k: len(sequences[k]))
    numbers = sorted(sequences[best_key])
    
    prefix, suffix = best_key
    # Detect padding from the actual filenames, not just the first number
    sample_files = [f for f in images if f.startswith(prefix) and f.endswith(suffix)]
    if sample_files:
        # Find the number part in the first file and measure its length
        first_file = sample_files[0]
        number_match = re.search(r'(\d+)', first_file)
        if number_match:
            padding = len(number_match.group(1))
        else:
            padding = len(str(numbers[0]))
    else:
        padding = len(str(numbers[0]))

    return {
        'prefix': prefix,
        'suffix': suffix,
        'start': numbers[0],
        'end': numbers[-1],
        'padding': padding,
        'pattern': f"{prefix}%0{padding}d{suffix}",
        'count': len(numbers),
        'files': sample_files,
    }


def validate_ffmpeg_installed() -> bool:
    """Check if FFmpeg is installed and accessible."""
    import subprocess
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.returncode == 0
    except (subprocess.SubprocessError, FileNotFoundError):
        return False


def get_ffmpeg_version() -> Optional[str]:
    """Get FFmpeg version string."""
    import subprocess
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.split('\n')[0]
    except (subprocess.SubprocessError, FileNotFoundError):
        pass
    return None


def estimate_output_size(
    width: int,
    height: int,
    fps: float,
    duration_seconds: float,
    codec: str,
    crf: int = 23,
) -> float:
    """Estimate output file size in MB."""
    base_bitrates = {
        'libx264': 5000,
        'libx265': 3500,
        'prores_ks': 50000,
        'libvpx-vp9': 4000,
    }
    
    base = base_bitrates.get(codec, 5000)
    resolution_factor = (width * height) / (1920 * 1080)
    crf_factor = 1.0 + (23 - crf) * 0.1
    bitrate = base * resolution_factor * crf_factor
    size_mb = (bitrate * duration_seconds) / 8 / 1024
    
    return size_mb


def format_duration(seconds: float) -> str:
    """Format duration as HH:MM:SS.mmm."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"
    elif minutes > 0:
        return f"{minutes:02d}:{secs:06.3f}"
    else:
        return f"{secs:.3f}s"


def format_filesize(size_mb: float) -> str:
    """Format file size in human-readable format."""
    if size_mb >= 1024:
        return f"{size_mb / 1024:.2f} GB"
    elif size_mb >= 1:
        return f"{size_mb:.2f} MB"
    else:
        return f"{size_mb * 1024:.2f} KB"


def get_image_sequence_path(directory: str, pattern_info: dict) -> str:
    """Get the FFmpeg input path for an image sequence."""
    dir_path = Path(directory)
    pattern = pattern_info['pattern']
    return str(dir_path / pattern)
