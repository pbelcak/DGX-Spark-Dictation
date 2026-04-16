"""CLI entry point for Sparktate daemon."""

from typing import Optional

import typer
from rich.console import Console

from .daemon import run_daemon

app = typer.Typer(
    name="sparktate",
    help="Push-to-talk speech-to-text daemon for DGX Spark",
    add_completion=False,
)
console = Console()


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
    """Run the push-to-talk transcription daemon.

    Press the trigger key (default: Right Alt) to start recording.
    Press it again to stop and paste transcription into active application.
    Press Escape to cancel without transcribing.
    """
    console.print("[bold blue]Sparktate[/bold blue] - DGX Spark Dictation")
    console.print()
    console.print(f"[dim]Trigger key:[/dim] {trigger}")
    console.print(f"[dim]Cancel key:[/dim] Escape")
    console.print(f"[dim]Notifications:[/dim] {'disabled' if no_notify else 'enabled'}")
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


def main() -> None:
    """Entry point."""
    app()


if __name__ == "__main__":
    main()
