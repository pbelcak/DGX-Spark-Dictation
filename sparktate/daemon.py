"""Background daemon for push-to-talk transcription."""

import enum
import subprocess
import threading
import time
from typing import Callable

import pyperclip
from pynput import keyboard
from pynput.keyboard import Controller, Key

from .audio import AudioCapture
from .transcriber import Transcriber


class State(enum.Enum):
    """Daemon state."""
    IDLE = "idle"
    RECORDING = "recording"
    TRANSCRIBING = "transcribing"


class TranscriptionDaemon:
    """
    Background daemon that listens for hotkeys to control transcription.

    - Press trigger key to start recording
    - Press trigger key again to stop and paste transcription
    - Press Escape to cancel recording without transcribing
    """

    def __init__(
        self,
        trigger_key: keyboard.Key = keyboard.Key.alt_r,
        cancel_key: keyboard.Key = keyboard.Key.esc,
        model_name: str | None = None,
        audio_device: int | None = None,
        on_state_change: Callable[[State, str], None] | None = None,
        notify: bool = True,
    ):
        """
        Initialize the daemon.

        Args:
            trigger_key: Key to start/stop recording
            cancel_key: Key to cancel recording
            model_name: ASR model to use
            audio_device: Audio input device index
            on_state_change: Callback when state changes (state, message)
            notify: Whether to show desktop notifications
        """
        self.trigger_key = trigger_key
        self.cancel_key = cancel_key
        self.model_name = model_name
        self.audio_device = audio_device
        self.on_state_change = on_state_change or self._default_state_handler
        self._notify_enabled = notify
        self._trigger_name = self._get_key_name(trigger_key)

        self._state = State.IDLE
        self._transcriber: Transcriber | None = None
        self._audio: AudioCapture | None = None
        self._listener: keyboard.Listener | None = None
        self._keyboard = Controller()
        self._running = False
        self._lock = threading.Lock()

    def _get_key_name(self, key: keyboard.Key) -> str:
        """Get human-readable name for a key."""
        name = key.name if hasattr(key, 'name') else str(key)
        # Convert alt_r -> Right Alt, f12 -> F12, etc.
        if '_' in name:
            parts = name.split('_')
            if parts[1] in ('r', 'l'):
                side = 'Right' if parts[1] == 'r' else 'Left'
                return f"{side} {parts[0].title()}"
        return name.upper()

    def _default_state_handler(self, state: State, message: str) -> None:
        """Default state change handler - prints to console."""
        print(f"[{state.value}] {message}")

    def _notify(self, title: str, message: str, urgency: str = "normal") -> None:
        """Send desktop notification."""
        if not self._notify_enabled:
            return
        try:
            subprocess.run(
                ["notify-send", "-u", urgency, "-a", "Sparktate", title, message],
                check=False,
                capture_output=True,
            )
        except FileNotFoundError:
            pass  # notify-send not available

    def _set_state(self, state: State, message: str) -> None:
        """Update state and notify."""
        self._state = state
        self.on_state_change(state, message)

    def _on_key_press(self, key: keyboard.Key | keyboard.KeyCode) -> None:
        """Handle key press events."""
        with self._lock:
            if key == self.trigger_key:
                if self._state == State.IDLE:
                    self._start_recording()
                elif self._state == State.RECORDING:
                    self._stop_and_transcribe()
            elif key == self.cancel_key:
                if self._state == State.RECORDING:
                    self._cancel_recording()

    def _start_recording(self) -> None:
        """Start audio recording."""
        self._set_state(State.RECORDING, "Recording started...")
        self._notify("Listening...", f"Speak now. Press {self._trigger_name} to finish.", "normal")

        self._audio = AudioCapture(device=self.audio_device)
        self._audio.start()

    def _stop_and_transcribe(self) -> None:
        """Stop recording and transcribe."""
        if self._audio is None:
            return

        self._set_state(State.TRANSCRIBING, "Transcribing...")
        self._notify("Transcribing", "Please wait...", "low")

        all_audio = self._audio.get_all_audio()
        duration = self._audio.get_duration()

        self._audio.stop()
        self._audio = None

        if len(all_audio) == 0 or duration < 0.5:
            self._set_state(State.IDLE, "No audio recorded")
            self._notify("Cancelled", "Recording too short", "normal")
            return

        def do_transcribe():
            try:
                text = self._transcriber.transcribe(all_audio)
                if text.strip():
                    pyperclip.copy(text)
                    self._paste()
                    self._set_state(State.IDLE, f"Pasted: {text[:50]}{'...' if len(text) > 50 else ''}")
                    self._notify("Transcribed & Pasted", text[:100], "normal")
                else:
                    self._set_state(State.IDLE, "No speech detected")
                    self._notify("No speech", "No speech was detected", "normal")
            except Exception as e:
                self._set_state(State.IDLE, f"Error: {e}")
                self._notify("Error", str(e), "critical")

        threading.Thread(target=do_transcribe, daemon=True).start()

    def _paste(self) -> None:
        """Simulate Ctrl+Shift+V to paste clipboard contents."""
        time.sleep(0.15)  # Wait for trigger key to be released
        self._keyboard.press(Key.ctrl)
        self._keyboard.press(Key.shift)
        self._keyboard.press('v')
        self._keyboard.release('v')
        self._keyboard.release(Key.shift)
        self._keyboard.release(Key.ctrl)

    def _cancel_recording(self) -> None:
        """Cancel recording without transcribing."""
        if self._audio:
            self._audio.stop()
            self._audio = None

        self._set_state(State.IDLE, "Recording cancelled")
        self._notify("Cancelled", "Recording cancelled", "low")

    def load_model(self) -> None:
        """Pre-load the ASR model."""
        self._transcriber = Transcriber(model_name=self.model_name)
        self._transcriber.load_model()

    def start(self) -> None:
        """Start the daemon."""
        if self._running:
            return

        self._running = True
        self._set_state(State.IDLE, f"Daemon started. Press {self._trigger_name} to record.")
        self._notify("Sparktate Ready", f"Press {self._trigger_name} to start recording", "normal")

        self._listener = keyboard.Listener(on_press=self._on_key_press)
        self._listener.start()

    def stop(self) -> None:
        """Stop the daemon."""
        self._running = False

        if self._audio:
            self._audio.stop()
            self._audio = None

        if self._listener:
            self._listener.stop()
            self._listener = None

        self._set_state(State.IDLE, "Daemon stopped")

    def run_forever(self) -> None:
        """Run the daemon until interrupted."""
        self.start()
        try:
            while self._running:
                time.sleep(0.1)
        except KeyboardInterrupt:
            pass
        finally:
            self.stop()


def run_daemon(
    model: str | None = None,
    device: int | None = None,
    trigger: str = "alt_r",
    verbose: bool = True,
    notify: bool = True,
) -> None:
    """
    Run the transcription daemon.

    Args:
        model: ASR model name
        device: Audio device index
        trigger: Trigger key name (alt_r, ctrl_r, f12, etc.)
        verbose: Print status messages
        notify: Show desktop notifications
    """
    key_map = {
        "alt_r": keyboard.Key.alt_r,
        "alt_l": keyboard.Key.alt_l,
        "ctrl_r": keyboard.Key.ctrl_r,
        "ctrl_l": keyboard.Key.ctrl_l,
        "shift_r": keyboard.Key.shift_r,
        "shift_l": keyboard.Key.shift_l,
        "f1": keyboard.Key.f1,
        "f2": keyboard.Key.f2,
        "f3": keyboard.Key.f3,
        "f4": keyboard.Key.f4,
        "f5": keyboard.Key.f5,
        "f6": keyboard.Key.f6,
        "f7": keyboard.Key.f7,
        "f8": keyboard.Key.f8,
        "f9": keyboard.Key.f9,
        "f10": keyboard.Key.f10,
        "f11": keyboard.Key.f11,
        "f12": keyboard.Key.f12,
    }

    trigger_key = key_map.get(trigger.lower(), keyboard.Key.alt_r)

    def state_handler(state: State, message: str) -> None:
        if verbose:
            icon = {"idle": "⏸", "recording": "🔴", "transcribing": "⏳"}
            print(f"{icon.get(state.value, '?')} [{state.value.upper()}] {message}")

    daemon = TranscriptionDaemon(
        trigger_key=trigger_key,
        model_name=model,
        audio_device=device,
        on_state_change=state_handler,
        notify=notify,
    )

    print("Loading ASR model...")
    daemon.load_model()
    print(f"Model loaded. Trigger key: {trigger}")
    print()

    daemon.run_forever()
