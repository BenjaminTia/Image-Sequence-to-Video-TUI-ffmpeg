"""FFmpeg converter logic for img2vid."""

import asyncio
import re
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from .models import ConversionConfig, FrameRange


@dataclass
class ConversionProgress:
    """Progress information during conversion."""
    current_frame: int = 0
    total_frames: int = 0
    fps: float = 0.0
    speed: float = 0.0
    time_elapsed: float = 0.0
    time_remaining: float = 0.0
    percent: float = 0.0

    @property
    def is_complete(self) -> bool:
        return self.percent >= 100.0


@dataclass
class ConversionResult:
    """Result of a conversion operation."""
    success: bool
    output_path: Optional[Path] = None
    error_message: Optional[str] = None
    final_stats: Optional[ConversionProgress] = None


class FFmpegConverter:
    """Handles FFmpeg conversion operations."""

    def __init__(self, config: ConversionConfig):
        self.config = config
        self._process: Optional[subprocess.Popen] = None
        self._cancelled = False
        self._concat_file: Optional[str] = None

    def __del__(self):
        """Clean up temporary files."""
        if self._concat_file:
            try:
                Path(self._concat_file).unlink()
            except:
                pass

    def build_command(self) -> list[str]:
        """Build the FFmpeg command from config."""
        from .utils import detect_sequence_pattern
        import platform

        cmd = ["ffmpeg", "-y"]

        cmd.append("-framerate")
        cmd.append(str(self.config.fps))

        # Get pattern info
        pattern_info = detect_sequence_pattern(self.config.input_directory)
        
        if pattern_info:
            dir_path = Path(self.config.input_directory)
            
            # On Windows, we need to use the pattern directly without glob
            # FFmpeg will automatically sort files alphabetically
            pattern = f"{pattern_info['prefix']}%0{pattern_info['padding']}d{pattern_info['suffix']}"
            input_path = str(dir_path / pattern)
            
            cmd.extend(["-i", input_path])
            
            # Apply frame range
            if self.config.frame_range:
                start_frame = self.config.frame_range.start
                end_frame = self.config.frame_range.end or pattern_info['end']
                
                if start_frame > pattern_info['start']:
                    cmd.extend(["-start_number", str(start_frame)])
                
                frame_count = end_frame - start_frame + 1
                cmd.extend(["-frames:v", str(frame_count)])
        else:
            # Fallback to generic pattern
            cmd.extend(["-i", self._get_input_pattern()])

        # Time range settings
        if self.config.time_range:
            if self.config.time_range.start_seconds > 0:
                cmd.extend(["-ss", f"{self.config.time_range.start_seconds:.3f}"])
            if self.config.time_range.duration_seconds:
                cmd.extend(["-t", f"{self.config.time_range.duration_seconds:.3f}"])

        # Video filter for scaling
        cmd.extend([
            "-vf",
            f"scale={self.config.resolution.width}:{self.config.resolution.height}"
        ])

        # Codec settings
        cmd.extend(["-c:v", self.config.output_settings.codec.value])
        cmd.extend(["-pix_fmt", self.config.output_settings.pixel_format.value])
        cmd.extend(["-preset", self.config.output_settings.preset])

        if self.config.output_settings.codec.value in ("libx264", "libx265", "libvpx-vp9"):
            cmd.extend(["-crf", str(self.config.output_settings.crf)])

        if self.config.output_settings.codec.value == "prores_ks":
            cmd.extend(["-profile:v", "3"])

        cmd.append(str(self.config.output_path))

        return cmd

    def _create_concat_file(self, files: list[str]) -> str:
        """Create a temporary concat file for FFmpeg."""
        dir_path = Path(self.config.input_directory).resolve()
        concat_content = ""
        for f in files:
            # Build absolute path and escape single quotes
            abs_path = str(dir_path / f).replace("'", "'\\''")
            concat_content += f"file '{abs_path}'\n"
        
        # Write to temp file
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False)
        temp_file.write(concat_content)
        temp_file.close()
        self._concat_file = temp_file.name
        return temp_file.name

    def _get_input_pattern(self) -> str:
        """Get the FFmpeg-compatible input pattern for sorted files."""
        from .utils import detect_sequence_pattern

        pattern_info = detect_sequence_pattern(self.config.input_directory)
        if not pattern_info:
            return str(Path(self.config.input_directory) / f"frame_%04d.png")

        dir_path = Path(self.config.input_directory)
        
        # Use glob pattern with sorted files
        # FFmpeg will automatically sort files when using glob
        pattern = f"{pattern_info['prefix']}%0{pattern_info['padding']}d{pattern_info['suffix']}"
        return str(dir_path / pattern)

    async def convert(
        self,
        progress_callback: Optional[Callable[[ConversionProgress], None]] = None,
    ) -> ConversionResult:
        """Run the conversion asynchronously."""
        self._cancelled = False
        cmd = self.build_command()

        try:
            self._process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            progress = ConversionProgress()
            output_lines = []
            
            while True:
                if self._process.stderr:
                    line = await self._process.stderr.readline()
                    if not line:
                        break
                    
                    line_str = line.decode('utf-8', errors='ignore').strip()
                    output_lines.append(line_str)
                    
                    parsed = self._parse_progress_line(line_str)
                    if parsed:
                        progress = parsed
                        if progress_callback:
                            progress_callback(progress)

            returncode = await self._process.wait()

            if returncode == 0:
                return ConversionResult(
                    success=True,
                    output_path=Path(self.config.output_path),
                    final_stats=progress,
                )
            else:
                error_msg = self._extract_error(output_lines)
                return ConversionResult(
                    success=False,
                    error_message=error_msg or f"FFmpeg exited with code {returncode}",
                )

        except asyncio.CancelledError:
            self.cancel()
            return ConversionResult(
                success=False,
                error_message="Conversion cancelled by user",
            )
        except Exception as e:
            return ConversionResult(
                success=False,
                error_message=str(e),
            )
        finally:
            self._process = None

    def _parse_progress_line(self, line: str) -> Optional[ConversionProgress]:
        """Parse a line of FFmpeg output for progress information."""
        if not line.startswith("frame="):
            return None

        progress = ConversionProgress()
        
        try:
            frame_match = self._extract_value(line, "frame=", "fps=")
            if frame_match:
                progress.current_frame = int(frame_match.strip())
            
            fps_match = self._extract_value(line, "fps=", "q=")
            if fps_match:
                progress.fps = float(fps_match.strip())
            
            time_match = self._extract_value(line, "time=", "bitrate=")
            if time_match:
                progress.time_elapsed = self._parse_time(time_match.strip())
            
            speed_match = self._extract_value(line, "speed=", "x")
            if speed_match:
                progress.speed = float(speed_match.strip())
            
            if self.config.frame_range and self.config.frame_range.end:
                total = self.config.frame_range.end - self.config.frame_range.start + 1
                progress.total_frames = total
                progress.percent = min(100.0, (progress.current_frame / total) * 100)

                if progress.speed > 0 and progress.fps > 0:
                    remaining_frames = total - progress.current_frame
                    progress.time_remaining = remaining_frames / (progress.fps * progress.speed)

        except (ValueError, IndexError):
            pass
        
        return progress

    def _extract_value(self, line: str, start_marker: str, end_marker: str) -> Optional[str]:
        """Extract a value between two markers in a string."""
        try:
            start_idx = line.find(start_marker) + len(start_marker)
            end_idx = line.find(end_marker, start_idx)
            if start_idx > 0 and end_idx > start_idx:
                return line[start_idx:end_idx]
        except ValueError:
            pass
        return None

    def _parse_time(self, time_str: str) -> float:
        """Parse FFmpeg time format to seconds."""
        try:
            parts = time_str.split(":")
            if len(parts) == 3:
                hours = int(parts[0])
                minutes = int(parts[1])
                seconds = float(parts[2])
                return hours * 3600 + minutes * 60 + seconds
        except ValueError:
            pass
        return 0.0

    def _extract_error(self, output_lines: list[str]) -> Optional[str]:
        """Extract error message from FFmpeg output."""
        for line in reversed(output_lines):
            lower = line.lower()
            if "error" in lower or "invalid" in lower or "failed" in lower:
                return line
        return None

    def cancel(self) -> None:
        """Cancel the current conversion."""
        self._cancelled = True
        if self._process:
            try:
                self._process.terminate()
            except ProcessLookupError:
                pass
