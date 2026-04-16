"""Audio capture using sounddevice."""

import queue
import threading
from typing import Callable

import numpy as np
import sounddevice as sd


class AudioCapture:
    """Captures audio from microphone, accumulating all audio from start."""

    SAMPLE_RATE = 16000  # Parakeet expects 16kHz
    CHANNELS = 1  # Mono audio
    DTYPE = np.float32

    def __init__(
        self,
        update_interval: float = 2.0,
        device: int | str | None = None,
    ):
        """
        Initialize audio capture.

        Args:
            update_interval: How often to signal new audio is ready (seconds)
            device: Audio input device (index or name). None for default.
        """
        self.update_interval = update_interval
        self.device = device
        self.update_samples = int(self.SAMPLE_RATE * update_interval)

        self._accumulated: list[np.ndarray] = []
        self._accumulated_samples = 0
        self._samples_since_last_update = 0
        self._update_event = threading.Event()
        self._stream: sd.InputStream | None = None
        self._running = False
        self._lock = threading.Lock()

    def _audio_callback(
        self,
        indata: np.ndarray,
        frames: int,
        time_info: dict,
        status: sd.CallbackFlags,
    ) -> None:
        """Callback for sounddevice stream."""
        if status:
            print(f"Audio status: {status}")

        with self._lock:
            self._accumulated.append(indata.copy().flatten())
            self._accumulated_samples += frames
            self._samples_since_last_update += frames

            # Signal when we have enough new audio
            if self._samples_since_last_update >= self.update_samples:
                self._samples_since_last_update = 0
                self._update_event.set()

    def start(self) -> None:
        """Start capturing audio."""
        if self._running:
            return

        self._running = True
        self._stream = sd.InputStream(
            samplerate=self.SAMPLE_RATE,
            channels=self.CHANNELS,
            dtype=self.DTYPE,
            device=self.device,
            callback=self._audio_callback,
            blocksize=int(self.SAMPLE_RATE * 0.1),  # 100ms blocks
        )
        self._stream.start()

    def stop(self) -> None:
        """Stop capturing audio."""
        self._running = False
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None

    def wait_for_update(self, timeout: float = 5.0) -> bool:
        """
        Wait for new audio to be available.

        Args:
            timeout: Maximum time to wait

        Returns:
            True if new audio is ready, False if timeout
        """
        result = self._update_event.wait(timeout=timeout)
        self._update_event.clear()
        return result

    def get_all_audio(self) -> np.ndarray:
        """Get all accumulated audio from the start of recording."""
        with self._lock:
            if not self._accumulated:
                return np.array([], dtype=self.DTYPE)
            return np.concatenate(self._accumulated)

    def get_duration(self) -> float:
        """Get duration of accumulated audio in seconds."""
        with self._lock:
            return self._accumulated_samples / self.SAMPLE_RATE

    def clear(self) -> None:
        """Clear accumulated audio (start fresh)."""
        with self._lock:
            self._accumulated = []
            self._accumulated_samples = 0
            self._samples_since_last_update = 0

    def get_level(self) -> float:
        """Get recent audio level (RMS)."""
        with self._lock:
            if not self._accumulated:
                return 0.0
            # Use last 0.1 seconds for level
            recent_samples = int(self.SAMPLE_RATE * 0.1)
            audio = np.concatenate(self._accumulated)
            if len(audio) < recent_samples:
                return float(np.sqrt(np.mean(audio**2)))
            return float(np.sqrt(np.mean(audio[-recent_samples:]**2)))

    @property
    def is_running(self) -> bool:
        """Check if capture is running."""
        return self._running

    def __enter__(self) -> "AudioCapture":
        self.start()
        return self

    def __exit__(self, *args) -> None:
        self.stop()


def list_devices() -> list[dict]:
    """List available audio input devices."""
    devices = []
    for i, dev in enumerate(sd.query_devices()):
        if dev["max_input_channels"] > 0:
            devices.append(
                {
                    "index": i,
                    "name": dev["name"],
                    "channels": dev["max_input_channels"],
                    "sample_rate": dev["default_samplerate"],
                }
            )
    return devices


def get_default_device() -> int | None:
    """Get the default input device index."""
    try:
        return sd.default.device[0]
    except Exception:
        return None
