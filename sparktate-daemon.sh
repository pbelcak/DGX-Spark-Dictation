#!/bin/bash
# Sparktate daemon launcher with logging

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SPARKTATE_DIR="$SCRIPT_DIR"
LOG_DIR="$SPARKTATE_DIR/logs"
VENV="$SPARKTATE_DIR/.venv"

# Create log directory if needed
mkdir -p "$LOG_DIR"

# Log file with timestamp
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="$LOG_DIR/sparktate_$TIMESTAMP.log"

# Kill any existing sparktate daemon
pkill -f "bin/sparktate" 2>/dev/null

# Activate venv and run daemon
source "$VENV/bin/activate"
exec sparktate >> "$LOG_FILE" 2>&1
