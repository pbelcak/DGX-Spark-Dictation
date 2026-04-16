# Sparktate

Live speech-to-text transcription for DGX Spark using NVIDIA Parakeet.

## Features

- **Daemon mode**: Background service with push-to-talk hotkey
- **Live mode**: Continuous transcription with real-time display
- Punctuation and capitalization (using Parakeet TDT-CTC model)
- Automatic clipboard copy
- GPU-accelerated inference
- Desktop notifications

## Requirements

- DGX Spark (or any Linux system with NVIDIA GPU)
- Python 3.10+
- CUDA toolkit
- PortAudio (for audio capture)

## Installation

Install system dependencies:

```bash
sudo apt install portaudio19-dev libnotify-bin
```

Install the package:

```bash
cd sparktate
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

The first run downloads the Parakeet model (~4GB) from HuggingFace.

## Usage

### Daemon Mode (Recommended)

Run as a background service with hotkey activation:

```bash
sparktate daemon
```

**Controls:**
- **Right Alt**: Start/stop recording
- **Escape**: Cancel recording (discard)
- **Ctrl+C**: Quit daemon

When you stop recording, the transcription is automatically copied to your clipboard with proper punctuation and capitalization.

**Options:**
```bash
sparktate daemon --help

Options:
  -m, --model TEXT      ASR model to use
  -d, --device INTEGER  Audio input device index
  -t, --trigger TEXT    Trigger key (alt_r, alt_l, ctrl_r, f12, etc.)
  -q, --quiet           Suppress console output (notifications only)
```

### Live Mode

Continuous transcription that re-processes all audio each interval:

```bash
sparktate listen
```

Speak into your microphone. The full transcript updates every 2 seconds and is copied to clipboard. Press `Ctrl+C` to stop.

**Options:**
```bash
sparktate listen --help

Options:
  -m, --model TEXT      ASR model (default: nvidia/parakeet-tdt_ctc-1.1b)
  -d, --device INTEGER  Audio input device index
  -i, --interval FLOAT  Update interval in seconds (default: 2.0)
  -g, --gpu TEXT        GPU device (e.g., cuda:0, cpu)
  --no-clipboard        Disable automatic clipboard copy
```

### Other Commands

```bash
# List audio input devices
sparktate devices

# Show system info (GPU, audio devices)
sparktate info

# Test audio capture
sparktate test
```

## Model Options

| Model | Parameters | Punctuation | Notes |
|-------|------------|-------------|-------|
| `nvidia/parakeet-tdt_ctc-1.1b` | 1.1B | Yes | **Default**, best quality |
| `nvidia/parakeet-tdt-0.6b-v3` | 600M | Yes | Multilingual (26 languages) |
| `nvidia/parakeet-tdt-1.1b` | 1.1B | No | Streaming-optimized |
| `nvidia/parakeet-ctc-1.1b` | 1.1B | No | Batch-oriented |

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Sparktate Daemon                         │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────┐                                           │
│  │ Hotkey       │  Right Alt → Start/Stop                   │
│  │ Listener     │  Escape → Cancel                          │
│  └──────┬───────┘                                           │
│         │                                                   │
│         ▼                                                   │
│  ┌──────────────┐   ┌──────────────┐   ┌────────────────┐  │
│  │ Audio Capture│──▶│ Accumulator  │──▶│ ASR Transcriber│  │
│  │ (sounddevice)│   │ (all audio)  │   │ (NeMo Parakeet)│  │
│  └──────────────┘   └──────────────┘   └───────┬────────┘  │
│                                                 │           │
│                                        ┌────────▼────────┐  │
│                                        │ Clipboard +     │  │
│                                        │ Notification    │  │
│                                        └─────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## Tips

- For long recordings, daemon mode is more efficient than live mode
- Use `--trigger f12` if Right Alt conflicts with your keyboard layout
- Run `sparktate devices` to find the correct microphone index
- The model is cached after first download (~4GB in `~/.cache/huggingface`)

## License

MIT
