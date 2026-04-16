"""Speech-to-text transcription using NVIDIA Parakeet."""

import tempfile
import wave

import numpy as np

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

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=True) as f:
            self._write_wav(f.name, audio)
            result = self._model.transcribe([f.name])

        return self._extract_text(result)

    def _extract_text(self, result: list) -> str:
        """Extract text from NeMo transcription result."""
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
        audio_int16 = (audio * 32767).astype(np.int16)

        with wave.open(path, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(self.SAMPLE_RATE)
            wf.writeframes(audio_int16.tobytes())
