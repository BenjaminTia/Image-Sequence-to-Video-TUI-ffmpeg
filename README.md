# img2vid

A **CLI-first** application for converting image sequences to video using FFmpeg. Includes an optional TUI mode for interactive use. Designed for easy integration into pipelines and scripts.

![Python Version](https://img.shields.io/badge/python-3.10%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

## Features

- 🖼️ **Automatic Sequence Detection** - Detects image sequences with numbered frames
- ⚙️ **Configurable Output** - Resolution, FPS, codec, format, and quality settings
- ✂️ **Trim Support** - Specify frame ranges to encode only portions
- 📊 **Real-time Progress** - Terminal progress bar with encoding speed and ETA
- 🔧 **CLI-First Design** - Easy integration into scripts, pipelines, and other programs
- 🎨 **Optional TUI** - Interactive terminal UI when needed
- 📦 **Portable** - Can be packaged as a standalone executable

## Quick Start

```bash
# Basic usage
img2vid ./renders/sequence_001 -o output.mp4

# With custom settings
img2vid ./renders/sequence_001 -o output.mp4 -r 1920x1080 -f 30 -c h264 --crf 18

# Trim frame range
img2vid ./renders/sequence_001 -o output.mp4 --frame-start 100 --frame-end 200

# Launch TUI mode
img2vid --tui
```

## Installation

### Prerequisites

- **Python 3.10+**
- **FFmpeg** installed and available in your PATH

### Install FFmpeg

**Windows:**
```powershell
winget install ffmpeg
# or
choco install ffmpeg
```

**macOS:**
```bash
brew install ffmpeg
```

**Linux:**
```bash
sudo apt install ffmpeg  # Ubuntu/Debian
sudo pacman -S ffmpeg    # Arch
sudo dnf install ffmpeg  # Fedora
```

### Install img2vid

```bash
git clone https://github.com/yourusername/img2vid.git
cd img2vid

python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # macOS/Linux

pip install -r requirements.txt
```

## CLI Usage

### Basic Command

```bash
img2vid <input_directory> [options]
```

### Options

| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `--output` | `-o` | Output video file path | `output.mp4` |
| `--resolution` | `-r` | Output resolution (WxH) | `1920x1080` |
| `--fps` | `-f` | Frames per second | `24` |
| `--frame-start` | | Start frame (auto if omitted) | Full sequence |
| `--frame-end` | | End frame (auto if omitted) | Full sequence |
| `--codec` | `-c` | Video codec | `h264` |
| `--format` | | Container format | `mp4` |
| `--crf` | | Quality (0-51) | `23` |
| `--preset` | | Encoding preset | `medium` |
| `--tui` | | Launch TUI mode | |
| `--verbose` | `-v` | Verbose output | |
| `--version` | | Show version | |

### Examples

**Convert a sequence with default settings:**
```bash
img2vid ./renders/my_sequence -o video.mp4
```

**4K ProRes for archival:**
```bash
img2vid ./renders/seq -o master.mov -r 3840x2160 -c prores --crf 0 --preset slow
```

**Web-optimized H.265:**
```bash
img2vid ./renders/seq -o web.mp4 -r 1920x1080 -c h265 --crf 28 -f 30
```

**Trim specific frames:**
```bash
img2vid ./renders/seq -o trimmed.mp4 --frame-start 50 --frame-end 150
```

**Use in a pipeline/script:**
```bash
#!/bin/bash
for seq in ./renders/*/; do
    img2vid "$seq" -o "${seq%/}.mp4" -c h264 --crf 23
done
```

### Exit Codes

| Code | Meaning |
|------|---------|
| `0` | Success |
| `1` | Error (invalid input, FFmpeg failure, etc.) |

## TUI Mode

Launch the interactive terminal UI:

```bash
img2vid --tui
```

### TUI Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `b` | Browse input directory |
| `o` | Browse output location |
| `c` | Start conversion |
| `d` | Toggle dark/light theme |
| `q` | Quit |

### Trim Modes

| Mode | Description |
|------|-------------|
| **Auto** | Uses full detected sequence (default) |
| **Frames** | Specify exact frame range (e.g., 1 to 240) |
| **Time** | Specify time range (e.g., 0:00 to 1:30) |

## Library Usage

Use img2vid as a Python library:

```python
from src.models import ConversionConfig, Resolution, OutputSettings, FrameRange, VideoCodec
from src.converter import FFmpegConverter
import asyncio

async def convert():
    config = ConversionConfig(
        input_directory="./renders/sequence",
        output_path="./output.mp4",
        resolution=Resolution(1920, 1080),
        fps=24,
        frame_range=FrameRange(start=1, end=240),
        output_settings=OutputSettings(
            codec=VideoCodec.H264,
            crf=18,
            preset="slow",
        ),
    )
    
    converter = FFmpegConverter(config)
    result = await converter.convert()
    
    if result.success:
        print(f"Done: {result.output_path}")

asyncio.run(convert())
```

## Project Structure

```
img2vid/
├── src/
│   ├── __init__.py       # Package
│   ├── main.py           # CLI entry point
│   ├── main_tui.py       # TUI application
│   ├── models.py         # Data classes
│   ├── converter.py      # FFmpeg logic
│   └── utils.py          # Utilities
├── tests/
│   ├── test_models.py
│   └── test_utils.py
├── pyproject.toml
├── requirements.txt
├── build.bat
└── README.md
```

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Format code
black src/ tests/

# Lint
ruff check src/ tests/

# Type check
mypy src/
```

## Build Executable

```bash
# Windows
build.bat

# Manual
pyinstaller --name img2vid --onefile src/main.py
```

## CRF Quality Guide

| CRF | Quality | Use Case |
|-----|---------|----------|
| 0-15 | Lossless | Archival, masters |
| 16-20 | High | Portfolio, presentations |
| 21-25 | Balanced | General use (default: 23) |
| 26-30 | Small | Web distribution |
| 31-51 | Lowest | Previews |

## Codec Guide

| Codec | Quality | Size | Speed | Compatibility |
|-------|---------|------|-------|---------------|
| H.264 | Good | Medium | Fast | Universal |
| H.265 | Better | Small | Medium | Modern devices |
| ProRes | Best | Large | Fast | Professional |
| VP9 | Good | Small | Slow | Web (YouTube) |

## Troubleshooting

**FFmpeg not found:**
```bash
ffmpeg -version  # Verify installation
```

**No sequence detected:**
Ensure images follow pattern: `frame_0001.png`, `img_001.exr`, etc.

**Encoding slow:**
- Use faster preset: `--preset fast` or `--preset ultrafast`
- Lower resolution or FPS
- Use H.264 instead of H.265

## License

MIT License

## Author

**Your Name**

- GitHub: [@yourusername](https://github.com/yourusername)
- Portfolio: [your-portfolio.com](https://your-portfolio.com)

---

*Built with Python and Textual*
