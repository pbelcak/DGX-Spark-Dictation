# DGX Spark Dictation

I tried virtually every Ubuntu dictation tool I could find. None of them were working on the combination of the NVIDIA GPU and ARM64 CPU that DGX Spark uses. So I created my own.

## How It Works

It's simple:

1. **Press Right Alt** to start recording
2. **Speak** into your microphone
3. **Press Right Alt again** to stop recording and automatically paste the transcription into your active application

That's it. The transcription uses NVIDIA's Parakeet model running locally on your DGX Spark's GPU, so it's fast and private.

**Cancel anytime** by pressing **Escape** instead of Right Alt.

**Desktop notifications** will show you the current state (recording, transcribing, done). These can be disabled with `--no-notify` if you prefer a quieter experience.

Have fun! Feel free to fork and add functionality if you find this useful. I'll be actively monitoring merge requests.

## Requirements

### Hardware
- **DGX Spark** (NVIDIA GB10 GPU + ARM64 CPU)

### System Dependencies
```bash
sudo apt install portaudio19-dev libnotify-bin xclip
```

- `portaudio19-dev` - Audio capture
- `libnotify-bin` - Desktop notifications
- `xclip` - Clipboard access (use `wl-clipboard` on Wayland)

### Python Dependencies

All Python dependencies are managed via `pyproject.toml`:

| Package | Purpose |
|---------|---------|
| `nemo_toolkit[asr]` | NVIDIA NeMo framework for ASR |
| `sounddevice` | Microphone audio capture |
| `numpy` | Audio array handling |
| `typer[all]` | CLI framework |
| `rich` | Console output formatting |
| `pyperclip` | Clipboard access |
| `pynput` | Global hotkey detection |

The NVIDIA Parakeet model (~4GB) is downloaded automatically on first run from HuggingFace.

## Installation

```bash
# Clone the repository
git clone git@github.com:pbelcak/DGX-Spark-Dictation.git
cd DGX-Spark-Dictation

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install
pip install -e .
```

## Usage

### Run Manually

```bash
sparktate daemon
```

### Run as Background Service (Auto-start on Login)

Create the launcher script:

```bash
cat > ~/sparktate-daemon.sh << 'EOF'
#!/bin/bash
SPARKTATE_DIR="$HOME/DGX-Spark-Dictation"  # Adjust path as needed
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

## Model Options

| Model | Parameters | Punctuation | Notes |
|-------|------------|-------------|-------|
| `nvidia/parakeet-tdt_ctc-1.1b` | 1.1B | Yes | **Default**, best quality |
| `nvidia/parakeet-tdt-0.6b-v3` | 600M | Yes | Multilingual (26 languages) |

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

## License

MIT
