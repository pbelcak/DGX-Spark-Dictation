"""CLI for Sparktate live transcription."""

import signal
import sys
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from .audio import AudioCapture, list_devices, get_default_device
from .display import SimpleDisplay
from .transcriber import Transcriber, check_gpu

app = typer.Typer(
    name="sparktate",
    help="Live speech-to-text transcription using NVIDIA Parakeet",
    add_completion=False,
)
console = Console()


@app.command()
def listen(
    model: str = typer.Option(
        "nvidia/parakeet-tdt_ctc-1.1b",
        "--model",
        "-m",
        help="ASR model to use (HuggingFace name or local path)",
    ),
    device: Optional[int] = typer.Option(
        None,
        "--device",
        "-d",
        help="Audio input device index (see 'sparktate devices')",
    ),
    interval: float = typer.Option(
        2.0,
        "--interval",
        "-i",
        help="Update interval in seconds (re-transcribes all audio each interval)",
    ),
    no_clipboard: bool = typer.Option(
        False,
        "--no-clipboard",
        help="Disable automatic clipboard copy",
    ),
    gpu: Optional[str] = typer.Option(
        None,
        "--gpu",
        "-g",
        help="GPU device (e.g., 'cuda:0', 'cpu')",
    ),
) -> None:
    """Start live transcription from microphone."""
    from rich.live import Live
    from rich.panel import Panel
    from rich.text import Text
    import pyperclip

    # Initialize transcriber
    console.print("[dim]Loading model...[/dim]")
    try:
        transcriber = Transcriber(model_name=model, device=gpu)
        transcriber.load_model()
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] Failed to load model: {e}")
        raise typer.Exit(1)

    console.print()
    console.print(f"[bold blue]Sparktate[/bold blue] - Live Transcription")
    console.print(f"[dim]Model:[/dim] {model}")
    console.print(f"[dim]Device:[/dim] {transcriber.device_info}")
    console.print(f"[dim]Mode:[/dim] Full re-transcription every {interval}s")
    console.print()

    # Set up audio capture (accumulates all audio)
    audio = AudioCapture(update_interval=interval, device=device)

    # Handle Ctrl+C gracefully
    running = True
    current_transcript = ""

    def signal_handler(sig, frame):
        nonlocal running
        running = False

    signal.signal(signal.SIGINT, signal_handler)

    def make_display(text: str, duration: float) -> Panel:
        content = Text(text if text else "(listening...)", style="white" if text else "dim italic")
        return Panel(
            content,
            title=f"[bold blue]Transcript[/bold blue] [dim]({duration:.1f}s)[/dim]",
            subtitle="[dim]Ctrl+C to stop[/dim]",
            border_style="blue",
        )

    # Main transcription loop
    try:
        with audio:
            with Live(make_display("", 0), refresh_per_second=4, console=console) as live:
                while running:
                    if not audio.wait_for_update(timeout=interval + 1.0):
                        continue

                    # Get ALL accumulated audio and transcribe it
                    all_audio = audio.get_all_audio()
                    if len(all_audio) == 0:
                        continue

                    duration = audio.get_duration()

                    try:
                        current_transcript = transcriber.transcribe(all_audio)
                        live.update(make_display(current_transcript, duration))

                        # Copy to clipboard
                        if not no_clipboard and current_transcript:
                            try:
                                pyperclip.copy(current_transcript)
                            except Exception:
                                pass
                    except Exception as e:
                        live.update(make_display(f"[Error: {e}]", duration))

    except KeyboardInterrupt:
        pass

    # Final output
    console.print()
    if current_transcript:
        console.print("[bold]Final transcript:[/bold]")
        console.print(current_transcript)
        console.print()

        if not no_clipboard:
            try:
                pyperclip.copy(current_transcript)
                console.print("[dim]Copied to clipboard.[/dim]")
            except Exception:
                pass


@app.command()
def devices() -> None:
    """List available audio input devices."""
    devs = list_devices()
    default = get_default_device()

    if not devs:
        console.print("[yellow]No audio input devices found.[/yellow]")
        raise typer.Exit(1)

    table = Table(title="Audio Input Devices")
    table.add_column("Index", style="cyan")
    table.add_column("Name", style="white")
    table.add_column("Channels", style="green")
    table.add_column("Sample Rate", style="yellow")
    table.add_column("Default", style="magenta")

    for dev in devs:
        is_default = "" if dev["index"] == default else ""
        table.add_row(
            str(dev["index"]),
            dev["name"],
            str(dev["channels"]),
            f"{int(dev['sample_rate'])} Hz",
            is_default,
        )

    console.print(table)
    console.print()
    console.print("[dim]Use --device INDEX with 'sparktate listen' to select a device[/dim]")


@app.command()
def info() -> None:
    """Show system information."""
    gpu_info = check_gpu()

    table = Table(title="System Information")
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="white")

    if gpu_info["available"]:
        table.add_row("GPU Available", "[green]Yes[/green]")
        table.add_row("GPU Count", str(gpu_info["device_count"]))
        table.add_row("GPU Name", gpu_info["device_name"])
        table.add_row("GPU Memory", f"{gpu_info['memory_total']} GB")
    else:
        table.add_row("GPU Available", f"[yellow]No[/yellow] ({gpu_info['reason']})")

    # Audio devices
    devs = list_devices()
    table.add_row("Audio Inputs", str(len(devs)))

    console.print(table)


@app.command()
def daemon(
    model: str = typer.Option(
        "nvidia/parakeet-tdt_ctc-1.1b",
        "--model",
        "-m",
        help="ASR model to use",
    ),
    device: Optional[int] = typer.Option(
        None,
        "--device",
        "-d",
        help="Audio input device index",
    ),
    trigger: str = typer.Option(
        "alt_r",
        "--trigger",
        "-t",
        help="Trigger key (alt_r, alt_l, ctrl_r, f12, etc.)",
    ),
    quiet: bool = typer.Option(
        False,
        "--quiet",
        "-q",
        help="Suppress console output",
    ),
    no_notify: bool = typer.Option(
        False,
        "--no-notify",
        "-n",
        help="Disable desktop notifications",
    ),
) -> None:
    """Run as background daemon with hotkey activation.

    Press the trigger key (default: Right Alt) to start recording.
    Press it again to stop and copy transcription to clipboard.
    Press Escape to cancel without transcribing.
    """
    from .daemon import run_daemon

    console.print("[bold blue]Sparktate Daemon[/bold blue]")
    console.print()
    console.print(f"[dim]Trigger key:[/dim] {trigger}")
    console.print(f"[dim]Cancel key:[/dim] Escape")
    console.print()
    console.print("[dim]Press Ctrl+C to quit[/dim]")
    console.print()

    try:
        run_daemon(
            model=model,
            device=device,
            trigger=trigger,
            verbose=not quiet,
            notify=not no_notify,
        )
    except KeyboardInterrupt:
        console.print("\n[dim]Daemon stopped.[/dim]")


@app.command()
def test(
    device: Optional[int] = typer.Option(
        None,
        "--device",
        "-d",
        help="Audio input device index",
    ),
    duration: float = typer.Option(
        3.0,
        "--duration",
        "-t",
        help="Recording duration in seconds",
    ),
) -> None:
    """Test audio capture (record and display levels)."""
    import time

    console.print(f"[bold]Testing audio capture for {duration} seconds...[/bold]")
    console.print("[dim]Speak into your microphone[/dim]")
    console.print()

    audio = AudioCapture(update_interval=duration, device=device)
    start = time.time()

    with audio:
        while time.time() - start < duration:
            level = audio.get_level()
            bar_width = int(level * 50 * 10)  # Scale for visibility
            bar = "█" * min(bar_width, 50)
            console.print(f"\r[green]{bar:<50}[/green] {level:.4f}", end="")
            time.sleep(0.05)

        console.print()
        console.print()

        # Get the accumulated audio
        all_audio = audio.get_all_audio()
        if len(all_audio) > 0:
            console.print(f"[green]Captured {len(all_audio)} samples ({len(all_audio)/16000:.2f}s)[/green]")
        else:
            console.print("[yellow]No audio captured[/yellow]")


def main() -> None:
    """Entry point."""
    app()


if __name__ == "__main__":
    main()
