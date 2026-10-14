# ExeBuilderStudio macOS distribution

`build_macos_distribution.sh` creates a native `.app` bundle and `.dmg` on a Mac only. It does not use cloud build services or GitHub Actions.

## Bundled into the app

- Python runtime and dependencies collected by PyInstaller from `requirements.txt` (including PySide6 and Pillow)
- The app's assets and Thai/Shan fonts
- A native `.icns` icon generated from `assets/logo.png`
- A SHA-256 checksum for the resulting DMG

## Build the release

1. Extract the project on a Mac.
2. Install Python 3.11 or 3.12 for the release build process.
3. Run from Terminal in the project root:

   ```bash
   bash macos/build_macos_distribution.sh
   ```

4. The output is in `macos_release/`, for example `ExeBuilderStudio-1.1-macOS-arm64.dmg` for Apple Silicon or `ExeBuilderStudio-1.1-macOS-x86_64.dmg` for Intel.
5. Test the app from the DMG on a real Mac before distributing it.

When `create-dmg` is installed, the script uses it to place the app icon and Applications drop link in a styled DMG window. Otherwise, it falls back to macOS `hdiutil`; Homebrew and extra tools are not required.

Optional installation of `create-dmg` with Homebrew:

```bash
brew install create-dmg
```

The script builds for the architecture of the Mac running it. Build separately on Apple Silicon and Intel if you need both architectures.

## Optionally bundle a JDK

A JDK is not included by default to avoid an unnecessarily large download and to avoid redistributing a JDK without permission. If you have a redistributable full JDK 17+ matching the Mac architecture, run:

```bash
EBS_BUNDLE_JDK_HOME="/path/to/jdk" bash macos/build_macos_distribution.sh
```

The JDK is copied to `ExeBuilderStudio.app/Contents/Resources/tools/jdk`, which the app's JDK selector discovers automatically.

## Target build tool requirements

- **Java JAR → DMG:** Requires a JDK 17+ with `jpackage`, unless a compatible JDK is bundled.
- **Python project → DMG:** Requires Python 3 on the Mac to create a virtual environment and install PyInstaller and project dependencies. Internet access is needed if the target project's requirements must be downloaded.
- Bundling ExeBuilderStudio's own runtime does not automatically bundle every build toolchain needed by arbitrary user projects.

## Security note

This script does not code-sign or notarize the app, per the project's no-signing requirement. macOS may show a warning when opening an app downloaded from the internet.
