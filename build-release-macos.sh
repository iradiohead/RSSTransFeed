#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

PYTHON="${PYTHON:-python3}"
BUILD_ENV="${HOME}/Library/Caches/RSSTransFeed2-build"
VENV_PYTHON="${BUILD_ENV}/bin/python"

if [[ ! -x "$VENV_PYTHON" ]]; then
    echo "Creating isolated macOS build environment..."
    "$PYTHON" -m venv "$BUILD_ENV"
fi

echo "Installing application and packaging dependencies..."
"$VENV_PYTHON" -m pip install --upgrade pip
"$VENV_PYTHON" -m pip install \
    -r requirements.txt \
    -r requirements-build.txt \
    pytest

echo "Running tests..."
"$VENV_PYTHON" -m pytest

rm -rf build dist

echo "Building macOS application bundle..."
"$VENV_PYTHON" -m PyInstaller --noconfirm --clean RSSTransFeed.spec

APP_PATH="dist/RSSTransFeed.app"
if [[ ! -d "$APP_PATH" ]]; then
    echo "Build failed: ${APP_PATH} was not created." >&2
    exit 1
fi

echo "Applying an ad-hoc local signature..."
codesign --force --deep --sign - "$APP_PATH"

ARCH="$(uname -m)"
ARCHIVE="dist/RSSTransFeed-macos-${ARCH}.zip"
echo "Creating release archive..."
ditto -c -k --sequesterRsrc --keepParent "$APP_PATH" "$ARCHIVE"

echo
echo "Release ready:"
echo "  ${ROOT_DIR}/${ARCHIVE}"
echo "Users can extract the ZIP and open RSSTransFeed.app; Python is not required."
