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

> **Prerequisites:** Python 3.10+ and FFmpeg must be installed first. See [Installation](#installation) below.

```bash
# Basic usage (after installing with pip install -e .)
img2vid ./renders/sequence_001 -o output.mp4

# With custom settings
img2vid ./renders/sequence_001 -o output.mp4 -r 1920x1080 -f 30 -c h264 --crf 18

# Trim frame range
img2vid ./renders/sequence_001 -o output.mp4 --frame-start 100 --frame-end 200

# Launch TUI mode
img2vid-tui

# Or run directly without installing
python -m src.main ./renders/sequence_001 -o output.mp4
python -m src.main_tui
```

## Installation

### Prerequisites

- **Python 3.10+**
- **FFmpeg** installed and available in your PATH

### 1. Install FFmpeg

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

Verify FFmpeg is working:
```bash
ffmpeg -version
```

### 2. Clone the Repository

```bash
git clone https://github.com/BenjaminTia/Image-Sequence-to-Video-CLI.git
cd Image-Sequence-to-Video-CLI
```

### 3. Set Up a Virtual Environment

```bash
python -m venv venv

# Activate it:
venv\Scripts\activate      # Windows (CMD/PowerShell)
source venv/bin/activate   # macOS/Linux
```

### 4. Install Dependencies

```bash
# Install the package in editable mode (registers img2vid and img2vid-tui commands)
pip install -e .

# Or install only the Python dependencies (run via python -m src.main instead)
pip install -r requirements.txt
```

> **Note:** `pip install -e .` is recommended. It reads `pyproject.toml` and registers the `img2vid` and `img2vid-tui` shell commands so you can run them directly. If you only use `pip install -r requirements.txt`, use `python -m src.main` and `python -m src.main_tui` to run instead.

### Running Without Installing (Development Mode)

If you prefer not to install the package, run the scripts directly from the project root:

```bash
# CLI mode
python -m src.main ./renders/sequence_001 -o output.mp4

# TUI mode
python -m src.main_tui
```

## CLI Usage

### Basic Command

```bash
# If installed with pip install -e .
img2vid <input_directory> [options]

# If using pip install -r requirements.txt only
python -m src.main <input_directory> [options]
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
# If installed with pip install -e .
img2vid-tui

# If using pip install -r requirements.txt only
python -m src.main_tui
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
Image-Sequence-to-Video-CLI/
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

## Technical Highlights

- **Async architecture** - FFmpeg subprocess wrapped in `asyncio` for non-blocking encoding with real-time stdout parsing
- **Textual TUI framework** - Reactive widgets, keyboard bindings, and theming via the [Textual](https://github.com/Textualize/textual) library
- **Typed data models** - Dataclasses and enums (`VideoCodec`, `Resolution`, `FrameRange`) for safe config passing
- **Regex-based sequence detection** - Automatically identifies frame padding and numbering patterns (e.g., `frame_0001.png`, `img.0042.exr`)
- **Process management** - Proper FFmpeg subprocess lifecycle with stderr capture and exit code handling
- **Packagable** - PyInstaller-compatible for single-file distribution

## Development

```bash
# Install with dev dependencies
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
# Windows (runs build.bat which handles venv + PyInstaller automatically)
build.bat

# Manual (from project root, with venv active)
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

**`img2vid` command not found after install:**
```bash
# Make sure you used pip install -e . (not just pip install -r requirements.txt)
pip install -e .
# If using requirements.txt only, run via:
python -m src.main
```

**No sequence detected:**
Ensure images follow a numbered pattern: `frame_0001.png`, `img_001.exr`, etc.

**Encoding slow:**
- Use faster preset: `--preset fast` or `--preset ultrafast`
- Lower resolution or FPS
- Use H.264 instead of H.265

## License

MIT License

## Author

**Benjamin Tia**

- GitHub: [@BenjaminTia](https://github.com/BenjaminTia)

---

*Built with Python, Textual, and FFmpeg*
