"""In-app macOS update discovery and DMG download from GitHub Releases."""
from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import shutil
import tempfile
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, build_opener, HTTPSHandler, HTTPRedirectHandler

from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtCore import QUrl
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QProgressBar, QMessageBox

from app.services.tool_downloads import APP_VERSION, UPDATE_REPOSITORY, version_key


def _validate_https(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("Update URLs must use HTTPS.")
    return url


class _SafeRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        _validate_https(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


_OPENER = build_opener(HTTPSHandler(), _SafeRedirect())


def _get_json(url: str) -> dict:
    _validate_https(url)
    request = Request(url, headers={
        "User-Agent": "ExeBuilderStudio-macOS-Updater",
        "Accept": "application/vnd.github+json",
    })
    with _OPENER.open(request, timeout=25) as response:
        _validate_https(response.geturl())
        data = response.read(4 * 1024 * 1024 + 1)
    if len(data) > 4 * 1024 * 1024:
        raise ValueError("GitHub release metadata is unexpectedly large.")
    return json.loads(data.decode("utf-8"))


def _mac_arch() -> str:
    machine = platform.machine().lower()
    return "arm64" if machine in ("arm64", "aarch64") else "x86_64" if machine in ("x86_64", "amd64") else machine


def latest_macos_release() -> dict:
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", UPDATE_REPOSITORY):
        raise ValueError("The update repository setting is invalid.")
    release = _get_json(f"https://api.github.com/repos/{UPDATE_REPOSITORY}/releases/latest")
    if release.get("draft") or release.get("prerelease"):
        raise ValueError("The latest release is not a stable public release.")
    assets = release.get("assets", [])
    arch = _mac_arch()
    candidates = [
        item for item in assets
        if item.get("name", "").lower().endswith(".dmg")
        and "macos" in item.get("name", "").lower()
        and arch.lower() in item.get("name", "").lower()
        and item.get("browser_download_url")
    ]
    if not candidates:
        raise ValueError(f"No macOS DMG for {arch} was found in the latest GitHub Release.")
    asset = sorted(candidates, key=lambda item: item.get("name", ""))[0]
    digest = asset.get("digest", "")
    if not digest.startswith("sha256:") or not re.fullmatch(r"[0-9a-fA-F]{64}", digest[7:]):
        raise ValueError("The DMG does not have a GitHub SHA-256 digest. Re-upload the release asset.")
    tag = str(release.get("tag_name", "")).strip()
    version = tag.lstrip("vV")
    if not version or not re.search(r"\d", version):
        raise ValueError("The latest GitHub Release has no valid version tag.")
    return {
        "version": version,
        "tag": tag,
        "name": asset["name"],
        "url": asset["browser_download_url"],
        "sha256": digest[7:].lower(),
        "size": int(asset.get("size", 0)),
        "html_url": release.get("html_url", f"https://github.com/{UPDATE_REPOSITORY}/releases"),
        "architecture": arch,
    }


def download_dmg(release: dict, progress) -> Path:
    root = Path.home() / "Library" / "Application Support" / "ExeBuilderStudio" / "updates"
    root.mkdir(parents=True, exist_ok=True)
    filename = Path(release["name"]).name
    if filename != release["name"] or not filename.lower().endswith(".dmg"):
        raise ValueError("Invalid DMG filename in release metadata.")
    target = root / filename
    partial = root / (filename + ".part")
    digest = hashlib.sha256()
    try:
        request = Request(release["url"], headers={"User-Agent": "ExeBuilderStudio-macOS-Updater"})
        _validate_https(release["url"])
        with _OPENER.open(request, timeout=40) as response, partial.open("wb") as output:
            _validate_https(response.geturl())
            content_type = response.headers.get("Content-Type", "").lower()
            if "text/html" in content_type:
                raise ValueError("GitHub returned a web page instead of a DMG.")
            total = int(response.headers.get("Content-Length", "0"))
            done = 0
            progress.emit(0, total)
            while True:
                chunk = response.read(256 * 1024)
                if not chunk:
                    break
                output.write(chunk)
                digest.update(chunk)
                done += len(chunk)
                progress.emit(done, total)
        if not partial.is_file() or partial.stat().st_size == 0:
            raise ValueError("The DMG download is empty.")
        if total and partial.stat().st_size != total:
            raise ValueError("The DMG download is incomplete. Please try again.")
        if digest.hexdigest().lower() != release["sha256"]:
            raise ValueError("SHA-256 verification failed. The downloaded DMG was rejected.")
        # UDIF DMG images store the "koly" trailer signature 512 bytes from EOF.
        with partial.open("rb") as stream:
            stream.seek(-512, os.SEEK_END)
            if stream.read(4) != b"koly":
                raise ValueError("The downloaded file does not look like a valid macOS disk image.")
        partial.replace(target)
        return target
    except Exception:
        partial.unlink(missing_ok=True)
        raise


class MacUpdateWorker(QThread):
    phase = Signal(str)
    progress = Signal(int, int)
    completed = Signal(object)
    failed = Signal(str)

    def __init__(self, action: str, parent=None):
        super().__init__(parent)
        self.action = action

    def run(self):
        try:
            self.phase.emit("checking")
            release = latest_macos_release()
            release["is_update"] = version_key(release["version"]) > version_key(APP_VERSION)
            if not release["is_update"]:
                self.completed.emit({"current": True, "release": release})
                return
            if self.action == "check":
                self.completed.emit({"update": True, "release": release})
                return
            self.phase.emit("downloading")
            path = download_dmg(release, self.progress)
            self.completed.emit({"downloaded": True, "release": release, "path": str(path)})
        except Exception as exc:
            self.failed.emit(str(exc))


class MacUpdateCard(QWidget):
    """A macOS-specific updater that verifies and opens the published DMG."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.worker = None
        self.release = None
        self.setObjectName("MacUpdateCard")
        layout = QVBoxLayout(self)
        title = QLabel("macOS Software Updates")
        title.setStyleSheet("font-size: 16px; font-weight: 600;")
        layout.addWidget(title)
        self.status = QLabel("Installed version: " + APP_VERSION)
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        buttons = QHBoxLayout()
        self.check_button = QPushButton("Check for Updates")
        self.download_button = QPushButton("Download and Open DMG")
        self.download_button.setEnabled(False)
        self.check_button.clicked.connect(lambda: self.start("check"))
        self.download_button.clicked.connect(lambda: self.start("download"))
        buttons.addWidget(self.check_button)
        buttons.addWidget(self.download_button)
        layout.addLayout(buttons)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)
        self.note = QLabel(
            "Updates are downloaded from the official GitHub Release and SHA-256 verified. "
            "Because this build is not code-signed/notarized, the updater opens the DMG for you; "
            "quit the app and drag the new app into Applications to replace the old copy."
        )
        self.note.setWordWrap(True)
        layout.addWidget(self.note)

    def start(self, action):
        if self.worker and self.worker.isRunning():
            return
        self.check_button.setEnabled(False)
        self.download_button.setEnabled(False)
        self.progress_bar.setRange(0, 0)
        self.progress_bar.show()
        self.status.setText("Checking GitHub Releases…" if action == "check" else "Preparing update download…")
        self.worker = MacUpdateWorker(action, self)
        self.worker.phase.connect(self.on_phase)
        self.worker.progress.connect(self.on_progress)
        self.worker.completed.connect(self.on_complete)
        self.worker.failed.connect(self.on_failed)
        self.worker.finished.connect(self.on_finished)
        self.worker.start()

    def on_phase(self, phase):
        self.status.setText("Checking GitHub Releases…" if phase == "checking" else "Downloading update…")

    def on_progress(self, done, total):
        if total > 0:
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(min(100, int(done * 100 / total)))
            self.status.setText(f"Downloading update: {done / 1048576:.1f} / {total / 1048576:.1f} MB")
        else:
            self.progress_bar.setRange(0, 0)

    def on_complete(self, result):
        release = result["release"]
        self.release = release
        if result.get("current"):
            self.status.setText(f"You are up to date. Installed: {APP_VERSION}; latest: {release['version']}.")
            self.download_button.setEnabled(False)
            QMessageBox.information(self, "No update available", self.status.text())
        elif result.get("update"):
            self.status.setText(f"Update available: {APP_VERSION} → {release['version']} ({release['architecture']}).")
            self.download_button.setEnabled(True)
            QMessageBox.information(self, "Update available",
                f"ExeBuilderStudio {release['version']} is available.\n\nClick Download and Open DMG to download and verify the installer.")
        elif result.get("downloaded"):
            path = Path(result["path"])
            self.status.setText(f"Downloaded and verified: {path}")
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(100)
            self.download_button.setEnabled(False)
            QMessageBox.information(self, "Update downloaded",
                "The DMG was downloaded and its SHA-256 checksum verified.\n\n"
                "The app will now open the disk image. Quit ExeBuilderStudio, drag the new app "
                "into Applications and choose Replace if macOS asks.")
            if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(path))):
                QMessageBox.warning(self, "Could not open DMG", f"Open this file manually:\n{path}")

    def on_failed(self, error):
        self.status.setText("Update check/download failed: " + error)
        QMessageBox.warning(self, "macOS update failed", error)

    def on_finished(self):
        self.check_button.setEnabled(True)
        self.progress_bar.hide()
        if self.release and self.release.get("is_update"):
            self.download_button.setEnabled(bool(self.release))
        worker = self.worker
        self.worker = None
        if worker:
            worker.deleteLater()
