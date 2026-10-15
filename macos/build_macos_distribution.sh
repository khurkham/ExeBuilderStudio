#!/bin/bash
# Build the ExeBuilderStudio macOS .app and .dmg locally on a Mac.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "ERROR: ExeBuilderStudio for macOS must be packaged on a Mac. No cloud build is used."
  exit 2
fi

ARCH="$(uname -m)"
case "$ARCH" in
  arm64|x86_64) ;;
  *) echo "ERROR: Unsupported Mac architecture: $ARCH"; exit 2 ;;
esac

PYTHON_BIN="${PYTHON_BIN:-$(command -v python3 || true)}"
if [[ -z "$PYTHON_BIN" || ! -x "$PYTHON_BIN" ]]; then
  echo "ERROR: Install Python 3.11 or 3.12 on this Mac, then rerun this script."
  exit 2
fi

# Keep build files separate from application source files.
BUILD_ROOT="$ROOT/build/macos-distribution"
VENV="$BUILD_ROOT/venv"
DIST="$BUILD_ROOT/dist"
WORK="$BUILD_ROOT/work"
SPEC="$BUILD_ROOT/spec"
RELEASE="$ROOT/macos_release"
mkdir -p "$BUILD_ROOT" "$RELEASE"

if [[ ! -x "$VENV/bin/python" ]]; then
  "$PYTHON_BIN" -m venv "$VENV"
fi
"$VENV/bin/python" -m pip install --upgrade pip
"$VENV/bin/python" -m pip install -r "$ROOT/requirements.txt"

# Create a native ICNS icon from the source logo using the project's Pillow helper.
"$VENV/bin/python" - "$ROOT" <<'PY'
import sys
from pathlib import Path
root = Path(sys.argv[1])
from app.services.icon_support import prepare_icon
prepare_icon(str(root / "assets" / "logo.png"), root / "assets" / "app.icns", "macos")
PY

rm -rf "$DIST" "$WORK" "$SPEC"
mkdir -p "$DIST" "$WORK" "$SPEC"

# PyInstaller bundles the Python runtime and app dependencies into the .app.
"$VENV/bin/python" -m PyInstaller \
  --noconfirm --clean --windowed --onedir \
  --name ExeBuilderStudio \
  --distpath "$DIST" --workpath "$WORK" --specpath "$SPEC" \
  --icon "$ROOT/assets/app.icns" \
  --osx-bundle-identifier "com.khurkham.exebuilderstudio" \
  --add-data "$ROOT/assets:assets" \
  --collect-all PySide6 --collect-all shiboken6 --collect-all PIL \
  --hidden-import app.services.macos_builder \
  --hidden-import app.services.windows_native_builder \
  --hidden-import app.services.jdk_manager \
  --hidden-import app.services.tool_downloads \
  --hidden-import app.ui.download_ui \
  --hidden-import app.translations \
  --hidden-import ui_assets \
  "$ROOT/main.py"

APP="$DIST/ExeBuilderStudio.app"
if [[ ! -d "$APP" ]]; then
  echo "ERROR: PyInstaller did not create $APP"
  exit 1
fi

# Optionally bundle a full JDK. It must be a redistributable JDK for this Mac architecture.
if [[ -n "${EBS_BUNDLE_JDK_HOME:-}" ]]; then
  JDK_HOME="$(cd "$EBS_BUNDLE_JDK_HOME" && pwd)"
  if [[ ! -x "$JDK_HOME/bin/jpackage" || ! -x "$JDK_HOME/bin/java" ]]; then
    echo "ERROR: EBS_BUNDLE_JDK_HOME must point to a full JDK containing bin/java and bin/jpackage."
    exit 2
  fi
  if [[ -x /usr/bin/lipo ]]; then
    JDK_ARCHS="$(/usr/bin/lipo -archs "$JDK_HOME/bin/java" 2>/dev/null || true)"
    if [[ -n "$JDK_ARCHS" && "$JDK_ARCHS" != *"$ARCH"* ]]; then
      echo "ERROR: JDK architecture ($JDK_ARCHS) does not match this Mac ($ARCH)."
      exit 2
    fi
  fi
  mkdir -p "$APP/Contents/Resources/tools"
  /usr/bin/ditto "$JDK_HOME" "$APP/Contents/Resources/tools/jdk"
  echo "Bundled JDK: $JDK_HOME"
else
  echo "No JDK bundled. Java JAR builds will use a JDK installed on the user's Mac."
fi

# Prepare a clean staging folder for the installer disk image.
# The app is not code-signed or notarized by this script, per project requirements.
STAGE="$BUILD_ROOT/stage"
rm -rf "$STAGE"
mkdir -p "$STAGE"
/usr/bin/ditto "$APP" "$STAGE/ExeBuilderStudio.app"
VERSION="${APP_VERSION:-$(sed -n "s/^APP_VERSION = '\\([^']*\\)'.*/\\1/p" "$ROOT/app/services/tool_downloads.py" | head -n 1)}"
if [[ -z "$VERSION" ]]; then
  echo "Could not determine APP_VERSION from app/services/tool_downloads.py" >&2
  exit 1
fi
DMG="$RELEASE/ExeBuilderStudio-$VERSION-macOS-$ARCH.dmg"
rm -f "$DMG"

# Prefer create-dmg for a polished drag-and-drop window when it is installed.
# The built-in hdiutil fallback keeps this workflow usable without Homebrew or extra tools.
if command -v create-dmg >/dev/null 2>&1; then
  echo "Creating a styled DMG with create-dmg..."
  create-dmg \
    --volname "ExeBuilderStudio 1.1" \
    --window-size 640 420 \
    --icon-size 96 \
    --icon "ExeBuilderStudio.app" 170 190 \
    --app-drop-link 470 190 \
    --no-internet-enable \
    "$DMG" \
    "$STAGE"
else
  echo "create-dmg is not installed; using macOS hdiutil fallback."
  ln -s /Applications "$STAGE/Applications"
  /usr/bin/hdiutil create -volname "ExeBuilderStudio $VERSION" -srcfolder "$STAGE" -ov -format UDZO "$DMG"
fi

# Emit a checksum for users to verify the downloaded release file.
shasum -a 256 "$DMG" > "$DMG.sha256"
echo
echo "SUCCESS: $DMG"
echo "SHA256: $(awk '{print $1}' "$DMG.sha256")"
echo "This build targets $ARCH. Build separately on the other Mac architecture if needed."
