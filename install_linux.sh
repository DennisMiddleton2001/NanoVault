#!/usr/bin/env bash
set -euo pipefail

APP_NAME="NanoVault Sanctuary"
VERSION="1.3.0"
REQUIRED_PYTHON_MAJOR=3
REQUIRED_PYTHON_MINOR=10
VENV_DIR=".venv"

info()  { printf "\033[1;36m[INFO]\033[0m %s\n" "$*"; }
warn()  { printf "\033[1;33m[WARN]\033[0m %s\n" "$*"; }
error() { printf "\033[1;31m[ERROR]\033[0m %s\n" "$*" >&2; exit 1; }

ensure_wget() {
    if command -v wget >/dev/null 2>&1; then
        info "wget found: $(wget --version | head -n1)"
        return
    fi

    warn "wget not found. Attempting installation..."
    if command -v apt-get >/dev/null 2>&1; then
        sudo apt-get update && sudo apt-get install -y wget
    elif command -v dnf >/dev/null 2>&1; then
        sudo dnf install -y wget
    elif command -v pacman >/dev/null 2>&1; then
        sudo pacman -Sy --noconfirm wget
    else
        error "Could not automatically install wget. Please install wget using your package manager and re-run."
    fi
    info "wget installed successfully."
}

ensure_uv() {
    if command -v uv >/dev/null 2>&1; then
        return
    fi
    info "Installing uv for fast, reproducible Python and environment management..."
    wget -qO- https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
}

python_version_ok() {
    local bin="$1"
    command -v "$bin" >/dev/null 2>&1 || return 1
    "$bin" -c "import sys; sys.exit(0 if sys.version_info >= (${REQUIRED_PYTHON_MAJOR}, ${REQUIRED_PYTHON_MINOR}) else 1)" 2>/dev/null
}

ensure_python() {
    for candidate in python3 python3.12 python3.11 python3.10; do
        if python_version_ok "$candidate"; then
            PYTHON_BIN="$(command -v "$candidate")"
            info "Using compatible Python: $PYTHON_BIN ($("$PYTHON_BIN" --version))"
            return
        fi
    done

    warn "Python ${REQUIRED_PYTHON_MAJOR}.${REQUIRED_PYTHON_MINOR}+ not found. Installing Python 3.12 via uv..."
    ensure_uv
    uv python install 3.12
    PYTHON_BIN="$(uv python find 3.12)"
    info "Installed Python: $PYTHON_BIN ($("$PYTHON_BIN" --version))"
}

setup_venv_and_deps() {
    info "Creating isolated virtual environment in '$VENV_DIR'..."
    if command -v uv >/dev/null 2>&1; then
        uv venv --python "$PYTHON_BIN" "$VENV_DIR"
        if [ -f "requirements.txt" ]; then
            info "Installing dependencies from requirements.txt..."
            uv pip install --python "$VENV_DIR/bin/python" -r requirements.txt
        elif [ -f "pyproject.toml" ]; then
            info "Installing project dependencies from pyproject.toml..."
            uv pip install --python "$VENV_DIR/bin/python" -e .
        else
            warn "No requirements.txt or pyproject.toml found; skipping package install."
        fi
    else
        "$PYTHON_BIN" -m venv "$VENV_DIR"
        "$VENV_DIR/bin/python" -m pip install --upgrade pip
        if [ -f "requirements.txt" ]; then
            info "Installing dependencies from requirements.txt..."
            "$VENV_DIR/bin/pip" install -r requirements.txt
        elif [ -f "pyproject.toml" ]; then
            info "Installing project dependencies from pyproject.toml..."
            "$VENV_DIR/bin/pip" install -e .
        else
            warn "No requirements.txt or pyproject.toml found; skipping package install."
        fi
    fi
}

print_launch_instructions() {
    cat <<EOF

====================================================================
  $APP_NAME v$VERSION — Installation Complete
====================================================================
To configure the application, edit the config.json file as needed.

  1. Activate the virtual environment:
     source $VENV_DIR/bin/activate

  2. Launch config_ui.py to configure the application in your browser:
     python config_ui.py
   (Ensure you are in the virtual environment when running this.)

   3. Before closing the browser tab, click 'Apply' button in the UI to write your configuration 
     to config.json.


To start the server:

  1. Activate the virtual environment:
     source $VENV_DIR/bin/activate

  2. Launch the FastAPI server:
     python main.py

  3. Open your browser to:
     http://127.0.0.1:8000

====================================================================
EOF
}

main() {
    info "Starting $APP_NAME v$VERSION Linux installer..."
    ensure_wget
    ensure_python
    setup_venv_and_deps
    print_launch_instructions
}

main "$@"