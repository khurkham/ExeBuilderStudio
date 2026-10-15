# ExeBuilderStudio 1.1

A desktop app for building native Windows and macOS installers, with English, Thai, and Shan UI.

## Native build policy — no cloud build

ExeBuilderStudio builds installers **only on the matching operating system**. It does not upload projects to a cloud build service and does not require a GitHub build repository or access token.

| Tab | Where it can build | Main tools | Output |
|---|---|---|---|
| Java JAR → Setup Windows | Windows only | JDK 17+ with `jpackage` and Inno Setup 6/7 (no WiX or PowerShell required) | `*_Setup.exe` |
| Python → Setup Windows | Windows only | Python 3, PyInstaller, Inno Setup 6/7 | `*_Setup.exe` |
| Java JAR → Setup macOS | macOS only | JDK 17+ with `jpackage` | `*_Setup.dmg` |
| Python → Setup macOS | macOS only | Python 3, PyInstaller, `create-dmg` (if installed) or built-in macOS `hdiutil` | `*_Setup.dmg` |

If a user tries to build a Windows `.exe` on macOS, the app displays a prominent warning to build on Windows. If a user tries to build a macOS `.dmg` on Windows, it displays a prominent warning to build on a Mac. The build is stopped before packaging begins.

Choose a JAR or Python entry file/project folder, output folder, app name, and optional icon in the matching target tab. Python projects are packaged in directory mode, then included in the final installer.

### Choose the JDK version used for builds

In **Tools / Java**, use **JDK used for Java builds** to select an installed JDK (for example 17, 21, or 25). Click **Refresh JDK list** to rescan the machine, or **Browse JDK folder…** to choose a JDK home manually. Select the JDK root containing `bin/jpackage.exe` on Windows or `bin/jpackage` on macOS. JDK 17 or newer is required. Auto-detect lets the app search for an installed JDK automatically.

### If the app says JDK or jpackage was not found

Seeing `java version 25.0.3` does not guarantee that a full JDK is installed. `java.exe` under `Common Files\Oracle\Java\javapath` may only be a Java Runtime launcher. This version searches common JDK install locations automatically. If `jpackage.exe` is still missing, install a **full JDK 17 or newer** (for example, Temurin JDK) and set `JAVA_HOME` to the JDK root folder, such as `C:\Program Files\Eclipse Adoptium\jdk-21...`—not the `bin` folder and not `javapath`. Restart ExeBuilderStudio afterward.

Common development folders (`.venv`, `venv`, `.idea`, `.git`, `tests`, caches, `build`, and `dist`) are filtered from Python project bundles. Local secrets such as `.env*`, private keys, PFX, and P12 files are excluded.

## Start and package ExeBuilderStudio

On Windows, install Python 3.11/3.12 64-bit, extract the source, and run `Start.bat`. To build the app and installer locally, run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Build_Studio.ps1 -CreateInstaller
```

This requires Python and Inno Setup on the build machine. The installer is written to `installer_output`.

## Tests and limitations

Unit tests cover build services, Windows/macOS packaging helpers, and tool downloads. Native builds must be tested on their respective operating systems because platform packaging tools are OS-specific. Dynamic Python imports, unusual resource loading, and platform-specific dependencies may require project-specific adjustments.

### Build progress

The build screen now displays a horizontal progress bar and the current build phase. Packaging runs in a worker thread so the UI remains responsive. Percentages are estimates based on build stages and tool output; they are not exact percentages reported by the packaging tools.

## Build a distributable macOS app

On a Mac, install Python 3.11 or 3.12 for the release-build step, then run:

```bash
bash macos/build_macos_distribution.sh
```

The script uses PyInstaller to create `ExeBuilderStudio.app` with its Python runtime, PySide6, Pillow, fonts and app assets, then creates a `.dmg` under `macos_release/` for the current Mac architecture (Apple Silicon or Intel). When `create-dmg` is installed, the script creates a styled drag-and-drop DMG window with an Applications link; otherwise, it falls back to the macOS `hdiutil` command. Install the optional helper with `brew install create-dmg`. To bundle a redistributable JDK 17+ matching that architecture, set `EBS_BUNDLE_JDK_HOME` before running the script. See `macos/README.md` for details.

Bundling ExeBuilderStudio does not automatically bundle every target-project toolchain. Java JAR builds need a JDK 17+ with `jpackage` unless one is bundled; Python-project builds still need Python 3 on the Mac and may need internet access to install the target project's dependencies.



## macOS in-app updates
The macOS About tab includes Check for Updates. It checks the latest stable GitHub Release, selects a DMG for the current architecture (`arm64` or `x86_64`), downloads over HTTPS, verifies the GitHub SHA-256 digest, checks the DMG trailer, and opens the image for manual installation. Update `APP_VERSION` and `BUILD_REVISION` in `app/services/tool_downloads.py` for each release. This project build is not code-signed or notarized; the updater does not silently replace the running app.

### About-page updates
The original About content and its existing platform-specific card are retained. The cross-platform updater is appended below them; it detects Windows/macOS and selects the matching installer asset.
