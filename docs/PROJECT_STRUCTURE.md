# Project structure and modularization plan

This document records the current layout and the safe, incremental refactoring approach for ExeBuilderStudio.

## Current modules

- `main.py` — PySide6 application window, widgets, event handlers, and orchestration.
- `backend.py` — input validation, icon conversion, Java/Launch4j and installer helpers.
- `download_ui.py` — tool-download UI cards, updater/about UI, and download-tab translations.
- `tool_downloads.py` — tool download/install workflows and application version metadata.
- `signing.py` — code-signing and certificate helper functions.
- `ui_assets.py` — asset paths and Thai/Shan font loading.
- `assets/` — application icon, logo, and bundled fonts.
- `installer/` — Inno Setup installer definition.
- `tests/` — unit and Windows smoke tests.
- `Build_Studio.ps1` and `.github/workflows/` — packaging and release automation.

## Changes in this refactor

The first step extracts the large English/Thai/Shan label dictionary from `main.py` into `app/translations.py`. `main.py` imports the same dictionary, keeping the existing keys and language values unchanged. The original root entry point and other modules remain in place to preserve the current launch/build commands.

## Target layout (incremental)

```text
app/
  __init__.py
  translations.py       # UI labels for English, Thai, and Shan
core/                   # future extraction of build and validation logic
services/               # future extraction of downloads and signing workflows
ui/                     # future extraction of reusable widgets and screens
assets/
installer/
tests/
main.py                 # stable compatibility entry point
backend.py              # retained until imports/tests are migrated
download_ui.py          # retained until imports/tests are migrated
tool_downloads.py       # retained until imports/tests are migrated
signing.py              # retained until imports/tests are migrated
ui_assets.py            # retained until imports/tests are migrated
```

## Safety rules for subsequent steps

1. Keep `main.py`, current root-level module names, build scripts, and tests working while moving one concern at a time.
2. Do not move signing, download, or build operations until their imports and tests are migrated together.
3. Run the Python test suite and Windows packaging smoke test after each functional extraction.
4. Keep this work on a feature branch and review it in a pull request before merging to `main`.
