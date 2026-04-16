"""Audio capture using sounddevice."""

import threading

import numpy as np
import sounddevice as sd


class AudioCapture:
    """Captures audio from microphone, accumulating all audio from start."""

    SAMPLE_RATE = 16000  # Parakeet expects 16kHz
    CHANNELS = 1  # Mono audio
    DTYPE = np.float32

    def __init__(self, device: int | str | None = None):
        """
        Initialize audio capture.

        Args:
            device: Audio input device (index or name). None for default.
        """
        self.device = device
        self._accumulated: list[np.ndarray] = []
        self._accumulated_samples = 0
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
        with self._lock:
            self._accumulated.append(indata.copy().flatten())
            self._accumulated_samples += frames

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
