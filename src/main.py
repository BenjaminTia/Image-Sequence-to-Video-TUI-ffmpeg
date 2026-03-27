"""Main entry point for img2vid - CLI and TUI modes."""

import argparse
import sys
import asyncio
from pathlib import Path

from .models import (
    ConversionConfig,
    Resolution,
    OutputSettings,
    FrameRange,
    VideoCodec,
    ContainerFormat,
    PixelFormat,
)
from .converter import FFmpegConverter, ConversionProgress
from .utils import (
    detect_sequence_pattern,
    validate_ffmpeg_installed,
    get_ffmpeg_version,
    format_duration,
    format_filesize,
)


def print_progress(progress: ConversionProgress, total_frames: int) -> None:
    """Print progress bar to terminal."""
    bar_width = 40
    filled = int(bar_width * progress.percent / 100)
    bar = "█" * filled + "░" * (bar_width - filled)
    
    # Clear line and print progress
    sys.stdout.write("\r")
    sys.stdout.write(
        f"[{bar}] {progress.percent:5.1f}% | "
        f"Frame: {progress.current_frame}/{total_frames} | "
        f"FPS: {progress.fps:5.1f} | "
        f"Speed: {progress.speed:5.2f}x"
    )
    if progress.time_remaining > 0:
        sys.stdout.write(f" | ETA: {format_duration(progress.time_remaining)}")
    sys.stdout.flush()


def run_cli_conversion(config: ConversionConfig, verbose: bool = False) -> bool:
    """Run conversion in CLI mode."""
    print(f"\n{'='*60}")
    print("img2vid - Image Sequence to Video Converter")
    print(f"{'='*60}\n")
    
    # Check FFmpeg
    if not validate_ffmpeg_installed():
        print("ERROR: FFmpeg not found. Please install FFmpeg and add it to PATH.")
        return False
    
    print(f"FFmpeg: {get_ffmpeg_version()}")
    
    # Detect sequence
    sequence_info = detect_sequence_pattern(config.input_directory)
    if not sequence_info:
        print(f"ERROR: No image sequence found in: {config.input_directory}")
        return False
    
    print(f"\nInput Directory: {config.input_directory}")
    print(f"Detected: {sequence_info['count']} frames ({sequence_info['prefix']}*{sequence_info['suffix']})")
    
    # Apply frame range
    if config.frame_range:
        start = config.frame_range.start
        end = config.frame_range.end or sequence_info['end']
        print(f"Frame Range: {start} to {end}")
    else:
        print(f"Frame Range: {sequence_info['start']} to {sequence_info['end']} (full sequence)")
    
    print(f"\nOutput Settings:")
    print(f"  Path: {config.output_path}")
    print(f"  Resolution: {config.resolution}")
    print(f"  FPS: {config.fps}")
    print(f"  Codec: {config.output_settings.codec.value}")
    print(f"  Format: {config.output_settings.format.value}")
    print(f"  CRF: {config.output_settings.crf}")
    
    # Estimate output size
    duration = (sequence_info['count'] / config.fps) if sequence_info else 0
    est_size = estimate_output_size(
        config.resolution.width,
        config.resolution.height,
        config.fps,
        duration,
        config.output_settings.codec.value,
        config.output_settings.crf,
    )
    print(f"  Estimated Size: {format_filesize(est_size)}")
    
    print(f"\n{'='*60}")
    print("Starting conversion... Press Ctrl+C to cancel\n")
    
    # Run conversion
    converter = FFmpegConverter(config)
    
    async def run():
        total_frames = (
            config.frame_range.end - config.frame_range.start + 1
            if config.frame_range and config.frame_range.end
            else sequence_info['count'] if sequence_info else 0
        )
        
        def on_progress(progress: ConversionProgress):
            print_progress(progress, total_frames)
        
        result = await converter.convert(progress_callback=on_progress)
        return result
    
    try:
        result = asyncio.run(run())
        
        print("\n")  # Newline after progress
        print(f"{'='*60}")
        
        if result.success:
            print(f"SUCCESS: Video saved to {result.output_path}")
            if result.final_stats:
                print(f"Time elapsed: {format_duration(result.final_stats.time_elapsed)}")
            return True
        else:
            print(f"FAILED: {result.error_message}")
            return False
            
    except KeyboardInterrupt:
        converter.cancel()
        print("\n\nConversion cancelled by user.")
        return False


def estimate_output_size(width, height, fps, duration, codec, crf):
    """Estimate output file size."""
    from .utils import estimate_output_size as _estimate
    return _estimate(width, height, fps, duration, codec, crf)


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser for CLI mode."""
    parser = argparse.ArgumentParser(
        prog="img2vid",
        description="Convert image sequences to video using FFmpeg",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic conversion
  img2vid ./renders/sequence -o output.mp4

  # Specify resolution and FPS
  img2vid ./renders/sequence -o output.mp4 -r 1920x1080 -f 30

  # Trim frame range
  img2vid ./renders/sequence -o output.mp4 --frame-start 100 --frame-end 200

  # High quality ProRes
  img2vid ./renders/sequence -o output.mov -c prores --crf 0

  # Use TUI mode
  img2vid --tui
""",
    )
    
    parser.add_argument(
        "input_directory",
        nargs="?",
        help="Directory containing image sequence",
    )
    
    parser.add_argument(
        "-o", "--output",
        dest="output_path",
        help="Output video file path (default: output.mp4)",
    )
    
    parser.add_argument(
        "-r", "--resolution",
        default="1920x1080",
        help="Output resolution (e.g., 1920x1080, 1280x720)",
    )
    
    parser.add_argument(
        "-f", "--fps",
        type=float,
        default=24.0,
        help="Frames per second (default: 24)",
    )
    
    parser.add_argument(
        "--frame-start",
        type=int,
        help="Start frame (default: first detected frame)",
    )
    
    parser.add_argument(
        "--frame-end",
        type=int,
        help="End frame (default: last detected frame)",
    )
    
    parser.add_argument(
        "-c", "--codec",
        choices=["h264", "h265", "prores", "vp9"],
        default="h264",
        help="Video codec (default: h264)",
    )
    
    parser.add_argument(
        "--format",
        dest="container_format",
        choices=["mp4", "mkv", "mov", "webm"],
        default="mp4",
        help="Container format (default: mp4)",
    )
    
    parser.add_argument(
        "--crf",
        type=int,
        default=23,
        help="Quality (CRF 0-51, lower=better, default: 23)",
    )
    
    parser.add_argument(
        "--preset",
        default="medium",
        help="Encoding preset (default: medium)",
    )
    
    parser.add_argument(
        "--tui",
        action="store_true",
        help="Launch TUI mode instead of CLI",
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output",
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version="img2vid 0.1.0",
    )
    
    return parser


def main():
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args()
    
    # TUI mode
    if args.tui or not args.input_directory:
        from .main_tui import run_tui
        run_tui()
        return
    
    # Validate input
    if not args.input_directory:
        parser.print_help()
        sys.exit(1)
    
    if not Path(args.input_directory).exists():
        print(f"ERROR: Input directory not found: {args.input_directory}")
        sys.exit(1)
    
    # Parse resolution
    try:
        width, height = map(int, args.resolution.split("x"))
        resolution = Resolution(width, height)
    except ValueError:
        print(f"ERROR: Invalid resolution format: {args.resolution}")
        print("Use format: WIDTHxHEIGHT (e.g., 1920x1080)")
        sys.exit(1)
    
    # Map codec
    codec_map = {
        "h264": VideoCodec.H264,
        "h265": VideoCodec.H265,
        "prores": VideoCodec.PRORES,
        "vp9": VideoCodec.VP9,
    }
    
    # Map format
    format_map = {
        "mp4": ContainerFormat.MP4,
        "mkv": ContainerFormat.MKV,
        "mov": ContainerFormat.MOV,
        "webm": ContainerFormat.WEBM,
    }
    
    # Detect sequence for default frame range
    sequence_info = detect_sequence_pattern(args.input_directory)
    
    # Frame range
    frame_start = args.frame_start
    frame_end = args.frame_end
    
    # Auto-populate from detected sequence if not specified
    if sequence_info:
        if frame_start is None:
            frame_start = sequence_info['start']
        if frame_end is None:
            frame_end = sequence_info['end']
    
    frame_range = None
    if frame_start is not None:
        frame_range = FrameRange(start=frame_start, end=frame_end)
    
    # Default output path
    output_path = args.output_path or "output.mp4"
    
    # Create config
    config = ConversionConfig(
        input_directory=args.input_directory,
        output_path=output_path,
        resolution=resolution,
        fps=args.fps,
        frame_range=frame_range,
        output_settings=OutputSettings(
            codec=codec_map[args.codec],
            format=format_map[args.container_format],
            crf=args.crf,
            preset=args.preset,
        ),
    )
    
    # Validate
    errors = config.validate()
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        sys.exit(1)
    
    # Run conversion
    success = run_cli_conversion(config, verbose=args.verbose)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
