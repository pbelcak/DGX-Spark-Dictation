"""Console display and clipboard handling."""

from collections import deque
from datetime import datetime

import pyperclip
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.text import Text


class TranscriptionDisplay:
    """Handles console output for live transcription."""

    def __init__(
        self,
        max_history: int = 10,
        copy_to_clipboard: bool = True,
    ):
        """
        Initialize the display.

        Args:
            max_history: Number of recent transcriptions to show
            copy_to_clipboard: Whether to copy new text to clipboard
        """
        self.console = Console()
        self.max_history = max_history
        self.copy_to_clipboard = copy_to_clipboard

        self._history: deque[tuple[datetime, str]] = deque(maxlen=max_history)
        self._current_text = ""
        self._audio_level = 0.0
        self._is_listening = False
        self._full_transcript: list[str] = []

    def add_transcription(self, text: str) -> None:
        """Add a new transcription to the display."""
        if not text.strip():
            return

        text = text.strip()
        now = datetime.now()
        self._history.append((now, text))
        self._current_text = text
        self._full_transcript.append(text)

        if self.copy_to_clipboard:
            try:
                pyperclip.copy(text)
            except Exception:
                pass  # Clipboard may not be available

    def set_audio_level(self, level: float) -> None:
        """Update the audio level indicator."""
        self._audio_level = min(1.0, level * 10)  # Scale for visibility

    def set_listening(self, listening: bool) -> None:
        """Set whether we're actively listening."""
        self._is_listening = listening

    def get_full_transcript(self) -> str:
        """Get the complete transcript as a single string."""
        return " ".join(self._full_transcript)

    def copy_full_transcript(self) -> bool:
        """Copy the full transcript to clipboard."""
        try:
            pyperclip.copy(self.get_full_transcript())
            return True
        except Exception:
            return False

    def render(self) -> Panel:
        """Render the current display state."""
        table = Table.grid(padding=(0, 2))
        table.add_column(justify="left")
        table.add_column(justify="left")

        # Status indicator
        if self._is_listening:
            status = Text("LISTENING", style="bold green")
        else:
            status = Text("PAUSED", style="bold yellow")

        table.add_row("Status:", status)

        # Audio level bar
        level_bar = self._render_level_bar(self._audio_level)
        table.add_row("Audio:", level_bar)

        # Separator
        table.add_row("", "")

        # Recent transcriptions
        if self._history:
            table.add_row(
                Text("Recent:", style="bold"),
                Text(""),
            )
            for timestamp, text in self._history:
                time_str = timestamp.strftime("%H:%M:%S")
                table.add_row(
                    Text(time_str, style="dim"),
                    Text(text, style="white"),
                )
        else:
            table.add_row(
                Text("Waiting for speech...", style="dim italic"),
                Text(""),
            )

        # Clipboard indicator
        if self.copy_to_clipboard:
            table.add_row("", "")
            table.add_row(
                Text("Clipboard:", style="dim"),
                Text("Auto-copy enabled", style="dim green"),
            )

        return Panel(
            table,
            title="[bold blue]Sparktate[/bold blue]",
            subtitle="[dim]Ctrl+C to stop[/dim]",
            border_style="blue",
        )

    def _render_level_bar(self, level: float) -> Text:
        """Render an audio level bar."""
        width = 20
        filled = int(level * width)
        empty = width - filled

        bar = Text()
        bar.append("[" + "" * filled, style="green" if level < 0.7 else "red")
        bar.append("" * empty + "]", style="dim")
        return bar

    def print_startup(self, model: str, device: str) -> None:
        """Print startup information."""
        self.console.print()
        self.console.print(
            Panel(
                f"[bold]Model:[/bold] {model}\n[bold]Device:[/bold] {device}",
                title="[bold blue]Sparktate[/bold blue]",
                border_style="blue",
            )
        )
        self.console.print()

    def print_message(self, message: str, style: str = "white") -> None:
        """Print a message to the console."""
        self.console.print(f"[{style}]{message}[/{style}]")

    def print_error(self, message: str) -> None:
        """Print an error message."""
        self.console.print(f"[bold red]Error:[/bold red] {message}")

    def print_transcription(self, text: str) -> None:
        """Print a transcription in simple mode."""
        if text.strip():
            timestamp = datetime.now().strftime("%H:%M:%S")
            self.console.print(f"[dim]{timestamp}[/dim] {text}")


class SimpleDisplay:
    """Simple line-by-line display without Rich Live."""

    def __init__(self, copy_to_clipboard: bool = True):
        self.console = Console()
        self.copy_to_clipboard = copy_to_clipboard
        self._full_transcript: list[str] = []

    def add_transcription(self, text: str) -> None:
        """Add and display a transcription."""
        if not text.strip():
            return

        text = text.strip()
        self._full_transcript.append(text)

        timestamp = datetime.now().strftime("%H:%M:%S")
        self.console.print(f"[dim]{timestamp}[/dim] {text}")

        if self.copy_to_clipboard:
            try:
                pyperclip.copy(text)
            except Exception:
                pass

    def get_full_transcript(self) -> str:
        return " ".join(self._full_transcript)

    def copy_full_transcript(self) -> bool:
        try:
            pyperclip.copy(self.get_full_transcript())
            return True
        except Exception:
            return False

    def print_startup(self, model: str, device: str) -> None:
        self.console.print()
        self.console.print(f"[bold blue]Sparktate[/bold blue] - Live Transcription")
        self.console.print(f"[dim]Model:[/dim] {model}")
        self.console.print(f"[dim]Device:[/dim] {device}")
        self.console.print(f"[dim]Press Ctrl+C to stop[/dim]")
        self.console.print()

    def print_message(self, message: str, style: str = "white") -> None:
        self.console.print(f"[{style}]{message}[/{style}]")

    def print_error(self, message: str) -> None:
        self.console.print(f"[bold red]Error:[/bold red] {message}")
