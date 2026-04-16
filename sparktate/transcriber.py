"""Speech-to-text transcription using NVIDIA Parakeet."""

import tempfile
import wave
from pathlib import Path

import numpy as np

# NeMo imports - these will be available after installing nemo_toolkit[asr]
try:
    import nemo.collections.asr as nemo_asr
    import torch

    NEMO_AVAILABLE = True
except ImportError:
    NEMO_AVAILABLE = False


class Transcriber:
    """Transcribes audio using NVIDIA Parakeet model."""

    DEFAULT_MODEL = "nvidia/parakeet-tdt_ctc-1.1b"
    SAMPLE_RATE = 16000

    def __init__(self, model_name: str | None = None, device: str | None = None):
        """
        Initialize the transcriber.

        Args:
            model_name: HuggingFace model name or local path
            device: Device to use ('cuda', 'cpu', or specific GPU like 'cuda:0')
        """
        if not NEMO_AVAILABLE:
            raise RuntimeError(
                "NeMo toolkit not installed. Run: pip install nemo_toolkit[asr]"
            )

        self.model_name = model_name or self.DEFAULT_MODEL
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self._model = None

    def load_model(self) -> None:
        """Load the ASR model."""
        if self._model is not None:
            return

        # Load model from HuggingFace or local path
        if self.model_name.startswith("nvidia/") or "/" in self.model_name:
            self._model = nemo_asr.models.ASRModel.from_pretrained(
                model_name=self.model_name
            )
        else:
            self._model = nemo_asr.models.ASRModel.restore_from(self.model_name)

        self._model = self._model.to(self.device)
        self._model.eval()

    def transcribe(self, audio: np.ndarray) -> str:
        """
        Transcribe audio to text.

        Args:
            audio: Audio samples as float32 numpy array (16kHz, mono)

        Returns:
            Transcribed text
        """
        if self._model is None:
            self.load_model()

        # NeMo expects audio files, so we write to a temp file
        # This is simpler than trying to use the streaming API directly
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=True) as f:
            self._write_wav(f.name, audio)
            result = self._model.transcribe([f.name])

        # Result is a list of transcriptions
        if result and len(result) > 0:
            # Handle different return formats
            if isinstance(result[0], str):
                return result[0]
            elif hasattr(result[0], "text"):
                return result[0].text
            else:
                return str(result[0])
        return ""

    def transcribe_file(self, path: str | Path) -> str:
        """
        Transcribe an audio file.

        Args:
            path: Path to audio file (WAV, FLAC, etc.)

        Returns:
            Transcribed text
        """
        if self._model is None:
            self.load_model()

        result = self._model.transcribe([str(path)])
        if result and len(result) > 0:
            if isinstance(result[0], str):
                return result[0]
            elif hasattr(result[0], "text"):
                return result[0].text
            else:
                return str(result[0])
        return ""

    def _write_wav(self, path: str, audio: np.ndarray) -> None:
        """Write audio array to WAV file."""
        # Convert float32 [-1, 1] to int16
        audio_int16 = (audio * 32767).astype(np.int16)

        with wave.open(path, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(self.SAMPLE_RATE)
            wf.writeframes(audio_int16.tobytes())

    @property
    def is_loaded(self) -> bool:
        """Check if model is loaded."""
        return self._model is not None

    @property
    def device_info(self) -> str:
        """Get device information."""
        if not NEMO_AVAILABLE:
            return "NeMo not available"
        if torch.cuda.is_available():
            return f"CUDA: {torch.cuda.get_device_name(0)}"
        return "CPU"


def check_gpu() -> dict:
    """Check GPU availability and info."""
    if not NEMO_AVAILABLE:
        return {"available": False, "reason": "NeMo not installed"}

    import torch

    if not torch.cuda.is_available():
        return {"available": False, "reason": "CUDA not available"}

    return {
        "available": True,
        "device_count": torch.cuda.device_count(),
        "device_name": torch.cuda.get_device_name(0),
        "memory_total": torch.cuda.get_device_properties(0).total_memory // (1024**3),
    }
