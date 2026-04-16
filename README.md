# DGX Spark Dictation

I tried virtually every Ubuntu dictation tool I could find. None of them worked on the combination of NVIDIA GPU and ARM64 CPU that DGX Spark uses. So I built my own.

## How It Works

```
┌────────────────────────────────────────────────────────────────┐
│                        Sparktate                               │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│   ┌─────────────┐      Press Right Alt                         │
│   │   Hotkey    │ ──────────────────────┐                      │
│   │  Listener   │      Press Escape     │                      │
│   └─────────────┘ ─────────┐            │                      │
│                            │            ▼                      │
│                            │   ┌─────────────────┐             │
│                            │   │ Audio Capture   │             │
│                            │   │  (microphone)   │             │
│                            │   └────────┬────────┘             │
│                            │            │                      │
│                      ┌─────▼─────┐      │ Press Right Alt      │
│                      │  Cancel   │      │ again                │
│                      └───────────┘      ▼                      │
│                                  ┌──────────────┐              │
│                                  │  Transcribe  │              │
│                                  │  (Parakeet)  │              │
│                                  └──────┬───────┘              │
│                                         │                      │
│                                         ▼                      │
│                                  ┌──────────────┐              │
│                                  │ Auto-paste   │              │
│                                  │ into active  │              │
│                                  │ application  │              │
│                                  └──────────────┘              │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

It's dead simple:

1. **Press Right Alt** to start recording
2. **Speak** into your microphone
3. **Press Right Alt again** to stop — your words are transcribed and **automatically pasted** into whatever app you're using

That's it. No copying, no switching windows. Just talk and it appears.

The transcription runs locally on your DGX Spark's GPU using NVIDIA's Parakeet model. Fast, private, and surprisingly accurate — with proper punctuation and capitalization.

**Made a mistake?** Press **Escape** to cancel the recording.

**Desktop notifications** keep you informed (recording → transcribing → done). Don't like them? Use `--no-notify`.

---

Have fun with this! Feel free to fork and add functionality. I'll be actively monitoring pull requests.

---

## Requirements

### Hardware

- **DGX Spark** (NVIDIA GB10 GPU + ARM64 CPU)

### System Dependencies

```bash
sudo apt install portaudio19-dev libnotify-bin xclip
```

| Package | Why |
|---------|-----|
| `portaudio19-dev` | Audio capture from microphone |
| `libnotify-bin` | Desktop notifications |
| `xclip` | Clipboard access (use `wl-clipboard` on Wayland) |

### Python Dependencies

Managed via `pyproject.toml`:

| Package | Why |
|---------|-----|
| `nemo_toolkit[asr]` | NVIDIA NeMo framework — runs the Parakeet ASR model |
| `sounddevice` | Captures audio from your microphone |
| `numpy` | Audio signal processing |
| `typer[all]` | CLI framework |
| `rich` | Pretty console output |
| `pyperclip` | Clipboard operations |
| `pynput` | Global hotkey detection |

The Parakeet model (~4GB) downloads automatically on first run from HuggingFace.

---

## Installation

```bash
# Clone
git clone git@github.com:pbelcak/DGX-Spark-Dictation.git
cd DGX-Spark-Dictation

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install
pip install -e .
```

---

## Usage

### Quick Start

```bash
sparktate daemon
```

Then press **Right Alt**, speak, and press **Right Alt** again.

### Auto-start on Login

Create the launcher script:

```bash
cat > ~/sparktate-daemon.sh << 'EOF'
#!/bin/bash
SPARKTATE_DIR="$HOME/DGX-Spark-Dictation"
LOG_DIR="$SPARKTATE_DIR/logs"
VENV="$SPARKTATE_DIR/.venv"

mkdir -p "$LOG_DIR"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="$LOG_DIR/sparktate_$TIMESTAMP.log"

pkill -f "sparktate daemon" 2>/dev/null
source "$VENV/bin/activate"
exec sparktate daemon >> "$LOG_FILE" 2>&1
EOF
chmod +x ~/sparktate-daemon.sh
```

Create systemd user service:

```bash
mkdir -p ~/.config/systemd/user

cat > ~/.config/systemd/user/sparktate.service << EOF
[Unit]
Description=Sparktate Speech-to-Text Daemon
After=graphical-session.target

[Service]
Type=simple
ExecStart=$HOME/sparktate-daemon.sh
Restart=on-failure
RestartSec=5
Environment=DISPLAY=:1

[Install]
WantedBy=default.target
EOF

# Enable and start
systemctl --user daemon-reload
systemctl --user enable sparktate.service
systemctl --user start sparktate.service
```

### Options

```
sparktate daemon --help

Options:
  -m, --model TEXT      ASR model (default: nvidia/parakeet-tdt_ctc-1.1b)
  -d, --device INTEGER  Audio input device index
  -t, --trigger TEXT    Trigger key (alt_r, alt_l, ctrl_r, f12, etc.)
  -q, --quiet           Suppress console output
  -n, --no-notify       Disable desktop notifications
```

---

## Model Options

| Model | Size | Punctuation | Notes |
|-------|------|-------------|-------|
| `nvidia/parakeet-tdt_ctc-1.1b` | 1.1B | Yes | **Default** — best quality for English |
| `nvidia/parakeet-tdt-0.6b-v3` | 600M | Yes | Multilingual (26 languages) |

---

## Tested On

```
OS:           Ubuntu 24.04.4 LTS (Noble Numbat)
Kernel:       6.17.0-1014-nvidia
Architecture: aarch64 (ARM64)
GPU:          NVIDIA GB10
Driver:       580.126.09
CUDA:         13.0
Python:       3.12.3
```

---

## License

MIT
