"""TUI application for img2vid - Terminal-native interface."""

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Vertical, Horizontal
from textual.screen import Screen
from textual.widgets import (
    Header,
    Footer,
    Static,
    Input,
    Button,
    Select,
    Label,
    ProgressBar,
    DirectoryTree,
    RadioSet,
    RadioButton,
)
from textual import work

from pathlib import Path
from typing import Optional

from .models import (
    ConversionConfig,
    Resolution,
    OutputSettings,
    FrameRange,
    TimeRange,
    VideoCodec,
    ContainerFormat,
)
from .converter import FFmpegConverter, ConversionProgress, ConversionResult
from .utils import detect_sequence_pattern, validate_ffmpeg_installed, get_ffmpeg_version


class DirectorySelectScreen(Screen):
    """Screen for selecting a directory."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
        Binding("enter", "select", "Select"),
    ]

    def __init__(self, title: str = "Select Directory"):
        super().__init__()
        self.title = title

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static(f"[bold]{self.title}[/bold]", classes="title")
        yield DirectoryTree(".", id="dir-tree")
        yield Footer()

    def action_cancel(self) -> None:
        self.dismiss(None)

    def action_select(self) -> None:
        tree = self.query_one("#dir-tree", DirectoryTree)
        if tree.path:
            self.dismiss(str(tree.path))

    def on_directory_tree_directory_selected(self, event: DirectoryTree.DirectorySelected) -> None:
        self.dismiss(str(event.path))


class ConversionScreen(Screen):
    """Screen showing conversion progress."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
    ]

    def __init__(self, config: ConversionConfig):
        super().__init__()
        self.config = config
        self._converter: FFmpegConverter | None = None

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("[bold]Converting...[/bold]", classes="title")

        with Vertical(id="progress-container"):
            yield Static(f"Input:  {self.config.input_directory}", id="input-path")
            yield Static(f"Output: {self.config.output_path}", id="output-path")
            yield Static(f"Res: {self.config.resolution} @ {self.config.fps}fps", id="res-info")
            yield Static(f"Cmd: ffmpeg -y -framerate {self.config.fps} ...", id="cmd-info", classes="hint")
            yield Static("", id="status")
            yield ProgressBar(id="progress-bar", show_eta=True)

        yield Footer()

    def on_mount(self) -> None:
        self._start_conversion()

    @work(exclusive=True)
    async def _start_conversion(self) -> None:
        self._converter = FFmpegConverter(self.config)

        def on_progress(progress: ConversionProgress) -> None:
            self.app.call_next(self._update_progress, progress)

        result = await self._converter.convert(progress_callback=on_progress)
        self.app.call_next(self._conversion_complete, result)

    def _update_progress(self, progress: ConversionProgress) -> None:
        bar = self.query_one("#progress-bar", ProgressBar)
        bar.progress = progress.percent

        status = self.query_one("#status", Static)
        status.update(
            f"Frame: {progress.current_frame} | "
            f"FPS: {progress.fps:.1f} | "
            f"Speed: {progress.speed:.2f}x"
        )

    def _conversion_complete(self, result: ConversionResult) -> None:
        if result.success:
            self.notify(f"Done: {result.output_path}", severity="information")
        else:
            self.notify(f"Failed: {result.error_message}", severity="error")
        self.app.pop_screen()

    def action_cancel(self) -> None:
        if self._converter:
            self._converter.cancel()
        self.app.pop_screen()


class Img2VidTUI(App):
    """Terminal-native TUI for img2vid."""

    CSS = """
    Screen {
        background: $background;
    }

    #main-container {
        width: 100%;
        height: 100%;
        padding: 1 2;
    }

    .title {
        text-align: center;
        text-style: bold;
        padding: 1 0;
        margin-bottom: 1;
    }

    .panel {
        background: $surface;
        border: solid $primary;
        padding: 1 2;
        margin: 1 0;
    }

    .panel-title {
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }

    .field-row {
        height: 3;
        margin: 1 0;
    }

    .field-row Label {
        width: 14;
        content-align: right middle;
        padding-right: 1;
        color: $text-muted;
    }

    .field-row Input {
        width: 20;
    }

    .field-row Input#input-dir, .field-row Input#output-dir {
        width: 50;
    }

    .field-row Input#frame-start, .field-row Input#frame-end {
        width: 10;
    }

    .field-row Input#time-start, .field-row Input#time-end {
        width: 12;
    }

    .field-row Select {
        width: 25;
    }

    .field-row Button {
        margin-left: 1;
    }

    #sequence-info {
        background: $surface-darken-2;
        padding: 1 2;
        margin: 1 0;
    }

    #button-row {
        height: 3;
        align: center middle;
        margin: 2 0;
    }

    #button-row Button {
        margin: 0 3;
        min-width: 20;
    }

    #ffmpeg-status {
        dock: bottom;
        height: 3;
        background: $primary-background;
        padding: 0 2;
        content-align: left middle;
    }

    #progress-container {
        width: 80%;
        height: auto;
        align: center middle;
        padding: 2 0;
    }

    #progress-container Static {
        width: 100%;
        margin: 1 0;
    }

    #progress-bar {
        width: 100%;
        margin: 1 0;
    }

    .hint {
        color: $text-muted;
        padding-left: 1;
    }

    .separator {
        padding: 0 2;
        color: $text-muted;
    }

    #custom-res-row, #custom-fps-input {
        height: 3;
        margin: 1 0;
    }

    #custom-res-row Input {
        width: 15;
    }

    #trim-mode-row {
        height: 3;
        margin: 1 0;
    }

    #frame-range-row, #time-range-row {
        height: 3;
        margin: 1 0;
    }

    RadioSet {
        height: 3;
    }

    RadioButton {
        padding: 0 1;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("d", "toggle_dark", "Dark Mode"),
        Binding("c", "convert", "Convert"),
        Binding("b", "browse_input", "Browse In"),
        Binding("o", "browse_output", "Browse Out"),
    ]

    def __init__(self):
        super().__init__()
        self.input_directory: str = ""
        self.sequence_info: dict | None = None
        self.trim_mode: str = "auto"  # auto, frames, time

    def compose(self) -> ComposeResult:
        yield Header()

        with Container(id="main-container"):
            # Title
            yield Static(
                "╔═══════════════════════════════════════════════════════════╗\n"
                "║  img2vid - Image Sequence to Video Converter              ║\n"
                "╚═══════════════════════════════════════════════════════════╝",
                classes="title",
            )

            # FFmpeg status bar
            ffmpeg_ok = validate_ffmpeg_installed()
            ffmpeg_version = get_ffmpeg_version() or "Not found"
            status_color = "green" if ffmpeg_ok else "red"
            status_icon = "✓" if ffmpeg_ok else "✗"
            yield Static(
                f"[{status_color}] {status_icon} FFmpeg: {ffmpeg_version} [/{status_color}]",
                id="ffmpeg-status",
            )

            # Input Panel
            with Container(classes="panel"):
                yield Static("INPUT SETTINGS", classes="panel-title")

                with Horizontal(classes="field-row"):
                    yield Label("Input Dir:", id="dir-label")
                    yield Input(placeholder="/path/to/sequence", id="input-dir")
                    yield Button("Browse [b]", id="browse-in-btn", variant="default")

                yield Static("", id="sequence-info")

            # Output Panel
            with Container(classes="panel"):
                yield Static("OUTPUT SETTINGS", classes="panel-title")

                with Horizontal(classes="field-row"):
                    yield Label("Output Dir:", id="output-dir-label")
                    yield Input(placeholder="/output/directory", id="output-dir")
                    yield Button("Browse [o]", id="browse-out-btn", variant="default")

                with Horizontal(classes="field-row"):
                    yield Label("Filename:", id="filename-label")
                    yield Input(placeholder="output.mp4", id="output-filename", value="output.mp4")

                with Horizontal(classes="field-row"):
                    yield Label("Resolution:", id="res-label")
                    yield Select.from_values(
                        ["1280x720", "1920x1080", "2560x1440", "3840x2160", "custom"],
                        value="1920x1080",
                        id="resolution-select",
                    )

                with Horizontal(classes="field-row", id="custom-res-row"):
                    yield Label("Custom:", id="custom-res-label")
                    yield Input(placeholder="1920", id="custom-width", restrict=r"\d*")
                    yield Static("×", classes="separator")
                    yield Input(placeholder="1080", id="custom-height", restrict=r"\d*")

            # Settings Panel
            with Container(classes="panel"):
                yield Static("CONVERSION SETTINGS", classes="panel-title")

                with Horizontal(classes="field-row"):
                    yield Label("FPS:", id="fps-label")
                    yield Select.from_values(
                        ["16", "24", "25", "30", "50", "60", "custom"],
                        value="24",
                        id="fps-select",
                    )
                    yield Input(placeholder="fps", id="custom-fps", restrict=r"\d*", classes="custom-input")

                # Trim mode selection
                with Horizontal(classes="field-row", id="trim-mode-row"):
                    yield Label("Trim Mode:", id="trim-label")
                    yield RadioSet(
                        RadioButton("Auto (full sequence)", id="trim-auto", value=True),
                        RadioButton("Frames", id="trim-frames"),
                        RadioButton("Time", id="trim-time"),
                        id="trim-mode",
                    )

                # Frame range inputs (hidden by default)
                with Horizontal(classes="field-row", id="frame-range-row"):
                    yield Label("Frames:", id="frame-label")
                    yield Input(placeholder="start", id="frame-start", restrict=r"\d*")
                    yield Static("to", classes="separator")
                    yield Input(placeholder="end", id="frame-end", restrict=r"\d*")
                    yield Static("(leave empty for full)", classes="hint")

                # Time range inputs (hidden by default)
                with Horizontal(classes="field-row", id="time-range-row"):
                    yield Label("Time:", id="time-label")
                    yield Input(placeholder="0:00", id="time-start", restrict=r"[\d:]*")
                    yield Static("to", classes="separator")
                    yield Input(placeholder="1:30", id="time-end", restrict=r"[\d:]*")
                    yield Static("(MM:SS or HH:MM:SS)", classes="hint")

                with Horizontal(classes="field-row"):
                    yield Label("Codec:", id="codec-label")
                    yield Select.from_values(
                        ["h264", "h265", "prores", "vp9"],
                        value="h264",
                        id="codec-select",
                    )

                    yield Label("Container:", id="format-label", classes="hint")
                    yield Select.from_values(
                        ["mp4", "mkv", "mov", "webm"],
                        value="mp4",
                        id="format-select",
                    )

                with Horizontal(classes="field-row"):
                    yield Label("Quality (CRF):", id="crf-label")
                    yield Input(value="23", id="crf-input", restrict=r"\d*")
                    yield Static("(0-51, lower=better)", classes="hint")

            # Action Buttons
            with Horizontal(id="button-row"):
                yield Button("▶ Convert [c]", id="convert-btn", variant="success")
                yield Button("✕ Quit [q]", id="quit-btn", variant="error")

        yield Footer()

    def on_mount(self) -> None:
        """Initialize the app."""
        # Hide custom inputs
        self.query_one("#custom-res-row", Horizontal).display = False
        self.query_one("#custom-fps", Input).display = False
        # Hide trim inputs by default (auto mode)
        self.query_one("#frame-range-row", Horizontal).display = False
        self.query_one("#time-range-row", Horizontal).display = False

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "resolution-select":
            self.query_one("#custom-res-row", Horizontal).display = event.value == "custom"
        elif event.select.id == "fps-select":
            self.query_one("#custom-fps", Input).display = event.value == "custom"

    def on_radio_set_changed(self, event: RadioSet.Changed) -> None:
        """Handle trim mode selection."""
        if event.radio_set.id == "trim-mode":
            selected = event.radio_set.pressed_button.id if event.radio_set.pressed_button else "trim-auto"
            
            if selected == "trim-auto":
                self.trim_mode = "auto"
                self.query_one("#frame-range-row", Horizontal).display = False
                self.query_one("#time-range-row", Horizontal).display = False
            elif selected == "trim-frames":
                self.trim_mode = "frames"
                self.query_one("#frame-range-row", Horizontal).display = True
                self.query_one("#time-range-row", Horizontal).display = False
            elif selected == "trim-time":
                self.trim_mode = "time"
                self.query_one("#frame-range-row", Horizontal).display = False
                self.query_one("#time-range-row", Horizontal).display = True

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id

        if button_id == "browse-in-btn":
            self._browse_input()
        elif button_id == "browse-out-btn":
            self._browse_output()
        elif button_id == "convert-btn":
            self.action_convert()
        elif button_id == "quit-btn":
            self.exit()

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "input-dir":
            self.input_directory = event.value
            self._update_sequence_info()

    def _browse_input(self) -> None:
        def callback(path: str | None) -> None:
            if path:
                self.input_directory = path
                self.query_one("#input-dir", Input).value = path
                self._update_sequence_info()

        self.push_screen(DirectorySelectScreen("Select Input Directory"), callback)

    def _browse_output(self) -> None:
        def callback(path: str | None) -> None:
            if path:
                self.query_one("#output-dir", Input).value = path

        self.push_screen(DirectorySelectScreen("Select Output Directory"), callback)

    def _update_sequence_info(self) -> None:
        """Update sequence information display."""
        if not self.input_directory:
            return

        self.sequence_info = detect_sequence_pattern(self.input_directory)
        info_widget = self.query_one("#sequence-info", Static)

        if self.sequence_info:
            info = self.sequence_info
            duration = info['count'] / 24.0  # Assume 24fps for estimate
            info_widget.update(
                f"[green]✓ Detected:[/green] {info['count']} frames | "
                f"Pattern: {info['prefix']}*{info['suffix']} | "
                f"Range: {info['start']}-{info['end']} | "
                f"~{duration:.1f}s @ 24fps"
            )
        else:
            info_widget.update("[yellow]⚠ No sequence detected in folder[/yellow]")

    def _parse_time(self, time_str: str) -> Optional[float]:
        """Parse time string (MM:SS or HH:MM:SS) to seconds."""
        if not time_str:
            return None
        
        parts = time_str.strip().split(":")
        try:
            if len(parts) == 2:
                # MM:SS
                minutes = int(parts[0])
                seconds = float(parts[1])
                return minutes * 60 + seconds
            elif len(parts) == 3:
                # HH:MM:SS
                hours = int(parts[0])
                minutes = int(parts[1])
                seconds = float(parts[2])
                return hours * 3600 + minutes * 60 + seconds
        except ValueError:
            pass
        return None

    def action_convert(self) -> None:
        """Start the conversion process."""
        input_dir = self.query_one("#input-dir", Input).value
        if not input_dir or not Path(input_dir).exists():
            self.notify("Please select a valid input directory", severity="error")
            return

        # Build output path from directory + filename
        output_dir = self.query_one("#output-dir", Input).value
        output_filename = self.query_one("#output-filename", Input).value or "output.mp4"

        if output_dir:
            output_path = str(Path(output_dir) / output_filename)
        else:
            output_path = output_filename

        # Resolution
        res_select = self.query_one("#resolution-select", Select).value
        if res_select == "custom":
            width = int(self.query_one("#custom-width", Input).value or "1920")
            height = int(self.query_one("#custom-height", Input).value or "1080")
            resolution = Resolution(width, height)
        else:
            width, height = map(int, res_select.split("x"))
            resolution = Resolution(width, height)

        # FPS
        fps_select = self.query_one("#fps-select", Select).value
        if fps_select == "custom":
            fps = float(self.query_one("#custom-fps", Input).value or "24")
        else:
            fps = float(fps_select)

        # Trim settings based on mode
        frame_range = None
        time_range = None

        if self.trim_mode == "frames":
            frame_start_val = self.query_one("#frame-start", Input).value
            frame_end_val = self.query_one("#frame-end", Input).value
            
            if frame_start_val:
                frame_range = FrameRange(
                    start=int(frame_start_val),
                    end=int(frame_end_val) if frame_end_val else None,
                )
            elif self.sequence_info:
                # Auto-populate from detected sequence
                frame_range = FrameRange(
                    start=self.sequence_info['start'],
                    end=self.sequence_info['end'],
                )

        elif self.trim_mode == "time":
            time_start_val = self.query_one("#time-start", Input).value
            time_end_val = self.query_one("#time-end", Input).value
            
            start_seconds = self._parse_time(time_start_val) if time_start_val else 0.0
            end_seconds = self._parse_time(time_end_val) if time_end_val else None
            
            if start_seconds is not None:
                duration = None
                if end_seconds is not None and end_seconds > start_seconds:
                    duration = end_seconds - start_seconds
                
                time_range = TimeRange(
                    start_seconds=start_seconds,
                    duration_seconds=duration,
                )

        # Codec
        codec_map = {
            "h264": VideoCodec.H264,
            "h265": VideoCodec.H265,
            "prores": VideoCodec.PRORES,
            "vp9": VideoCodec.VP9,
        }
        codec = codec_map.get(self.query_one("#codec-select", Select).value, VideoCodec.H264)

        # Format
        format_map = {
            "mp4": ContainerFormat.MP4,
            "mkv": ContainerFormat.MKV,
            "mov": ContainerFormat.MOV,
            "webm": ContainerFormat.WEBM,
        }
        container_format = format_map.get(self.query_one("#format-select", Select).value, ContainerFormat.MP4)

        # CRF
        crf = int(self.query_one("#crf-input", Input).value or "23")
        crf = max(0, min(51, crf))

        config = ConversionConfig(
            input_directory=input_dir,
            output_path=output_path,
            resolution=resolution,
            fps=fps,
            frame_range=frame_range,
            time_range=time_range,
            output_settings=OutputSettings(
                codec=codec,
                format=container_format,
                crf=crf,
            ),
        )

        errors = config.validate()
        if errors:
            self.notify("\n".join(errors), severity="error")
            return

        self.push_screen(ConversionScreen(config))

    def action_toggle_dark(self) -> None:
        self.theme = "textual-dark" if self.theme == "textual-light" else "textual-light"

    def action_quit(self) -> None:
        self.exit()

    def action_browse_input(self) -> None:
        self._browse_input()

    def action_browse_output(self) -> None:
        self._browse_output()


def run_tui():
    """Run the TUI application."""
    app = Img2VidTUI()
    app.run()
