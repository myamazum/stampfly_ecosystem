#!/bin/bash
# StampFly Ecosystem Installer
# Usage: ./install.sh [options]
#
# This script checks for Python 3.10+ and then runs the Python installer.

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# WSL2 detection
# WSL2環境を検出
is_wsl() {
    [ -f /proc/version ] && grep -qi microsoft /proc/version
}

# Check system prerequisites (Debian/Ubuntu)
# システム前提条件チェック（Debian/Ubuntu）
check_prerequisites() {
    # ESP-IDF required packages for Debian/Ubuntu
    local required_packages="git cmake ninja-build python3-venv wget flex bison gperf ccache libffi-dev libssl-dev dfu-util libusb-1.0-0"

    if [ -f /etc/debian_version ]; then
        local missing=""
        for pkg in $required_packages; do
            if ! dpkg -s "$pkg" > /dev/null 2>&1; then
                missing="$missing $pkg"
            fi
        done

        if [ -n "$missing" ]; then
            error "Missing required packages:$missing"
            echo
            echo "  Install with:"
            echo -e "    ${BOLD}sudo apt update && sudo apt install -y$missing${NC}"
            echo
            exit 1
        fi
        success "All prerequisite packages installed"
    else
        # Non-Debian: check key commands only
        # 非Debian系: 主要コマンドのみ確認
        local missing_cmds=""
        for cmd_name in git cmake ninja python3 wget flex bison gperf ccache; do
            if ! command -v "$cmd_name" &> /dev/null; then
                missing_cmds="$missing_cmds $cmd_name"
            fi
        done

        if [ -n "$missing_cmds" ]; then
            error "Missing required commands:$missing_cmds"
            echo "  Please install these using your system package manager."
            echo
            exit 1
        fi
        success "All prerequisite commands found"
    fi
}

info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

success() {
    echo -e "${GREEN}[OK]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

header() {
    echo
    echo -e "${CYAN}============================================================${NC}"
    echo -e "${BOLD} $1${NC}"
    echo -e "${CYAN}============================================================${NC}"
    echo
}

# Check Python version
check_python() {
    local cmd=$1
    if command -v "$cmd" &> /dev/null; then
        local version
        version=$("$cmd" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null)
        local major
        major=$("$cmd" -c 'import sys; print(sys.version_info.major)' 2>/dev/null)
        local minor
        minor=$("$cmd" -c 'import sys; print(sys.version_info.minor)' 2>/dev/null)

        if [ "$major" -ge 3 ] && [ "$minor" -ge 10 ]; then
            echo "$cmd:$version"
            return 0
        fi
    fi
    return 1
}

# Find suitable Python
find_python() {
    for cmd in python3.12 python3.11 python3.10 python3 python; do
        result=$(check_python "$cmd") && {
            echo "$result"
            return 0
        }
    done
    return 1
}

# Install Python guidance
install_python_guidance() {
    echo
    error "Python 3.10+ is required but not found."
    echo

    case "$(uname -s)" in
        Darwin)
            echo "  Install Python using Homebrew:"
            echo "    ${BOLD}brew install python@3.12${NC}"
            echo
            echo "  Or download from:"
            echo "    https://www.python.org/downloads/"
            ;;
        Linux)
            if [ -f /etc/debian_version ]; then
                echo "  Install Python using apt:"
                echo "    ${BOLD}sudo apt update && sudo apt install python3.12${NC}"
            elif [ -f /etc/fedora-release ]; then
                echo "  Install Python using dnf:"
                echo "    ${BOLD}sudo dnf install python3.12${NC}"
            else
                echo "  Install Python using your package manager."
            fi
            echo
            echo "  Or use pyenv:"
            echo "    https://github.com/pyenv/pyenv"
            ;;
        *)
            echo "  Download Python from:"
            echo "    https://www.python.org/downloads/"
            ;;
    esac
    echo
}

# Main
header "StampFly Ecosystem Installer"

# WSL2 information
# WSL2環境の情報表示
if is_wsl; then
    info "WSL2 environment detected"
    echo
    echo "  Note: USB device access requires usbipd-win on Windows side."
    echo "  See: https://learn.microsoft.com/en-us/windows/wsl/connect-usb"
    echo
fi

# Check system prerequisites on Linux
# Linux環境のシステム前提条件チェック
if [ "$(uname -s)" = "Linux" ]; then
    info "Checking system prerequisites..."
    check_prerequisites
    echo
fi

info "Checking Python..."

PYTHON_RESULT=$(find_python) || {
    install_python_guidance
    exit 1
}

PYTHON_CMD="${PYTHON_RESULT%%:*}"
PYTHON_VERSION="${PYTHON_RESULT##*:}"

success "Found Python $PYTHON_VERSION ($PYTHON_CMD)"
echo

# Run Python installer
exec "$PYTHON_CMD" "$SCRIPT_DIR/scripts/installer.py" "$@"
