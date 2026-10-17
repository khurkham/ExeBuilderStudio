"""Cross-platform ExeBuilderStudio update discovery and verified installer download."""
from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import sys
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, build_opener, HTTPSHandler, HTTPRedirectHandler

from PySide6.QtCore import QThread, Signal, QUrl, QProcess
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QProgressBar, QMessageBox

from app.services.tool_downloads import APP_VERSION, UPDATE_REPOSITORY, version_key


def _https(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("Update URLs must use HTTPS.")
    return url


class _SafeRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        _https(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


_OPENER = build_opener(HTTPSHandler(), _SafeRedirect())


def _json(url: str) -> dict:
    _https(url)
    request = Request(url, headers={"User-Agent": "ExeBuilderStudio-Updater", "Accept": "application/vnd.github+json"})
    with _OPENER.open(request, timeout=25) as response:
        _https(response.geturl())
        raw = response.read(4 * 1024 * 1024 + 1)
    if len(raw) > 4 * 1024 * 1024:
        raise ValueError("GitHub release metadata is unexpectedly large.")
    return json.loads(raw.decode("utf-8"))


def current_platform_asset() -> dict:
    """Return latest stable release asset appropriate for this OS and Mac architecture."""
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", UPDATE_REPOSITORY):
        raise ValueError("The update repository setting is invalid.")
    release = _json(f"https://api.github.com/repos/{UPDATE_REPOSITORY}/releases/latest")
    if release.get("draft") or release.get("prerelease"):
        raise ValueError("The latest release is not a stable public release.")
    tag = str(release.get("tag_name", "")).strip()
    version = tag.lstrip("vV")
    if not version or not re.search(r"\d", version):
        raise ValueError("The latest GitHub Release has no valid version tag.")

    if sys.platform == "darwin":
        machine = platform.machine().lower()
        arch = "arm64" if machine in ("arm64", "aarch64") else "x86_64" if machine in ("x86_64", "amd64") else machine
        candidates = [a for a in release.get("assets", [])
                      if a.get("name", "").lower().endswith(".dmg")
                      and "macos" in a.get("name", "").lower()
                      and arch in a.get("name", "").lower()]
        expected_kind = "dmg"
    elif os.name == "nt":
        arch = platform.machine().lower()
        candidates = [a for a in release.get("assets", [])
                      if a.get("name", "").lower() == "exebuilderstudio_setup.exe"]
        expected_kind = "exe"
    else:
        raise ValueError("In-app updates are supported only on Windows and macOS.")

    candidates = [a for a in candidates if a.get("browser_download_url")]
    if not candidates:
        target = f"macOS {arch} DMG" if expected_kind == "dmg" else "ExeBuilderStudio_Setup.exe"
        raise ValueError(f"The latest GitHub Release does not contain the required {target}.")
    asset = sorted(candidates, key=lambda a: a.get("name", ""))[0]
    digest = str(asset.get("digest", ""))
    if not digest.startswith("sha256:") or not re.fullmatch(r"[0-9a-fA-F]{64}", digest[7:]):
        raise ValueError("The release asset has no valid GitHub SHA-256 digest. Re-upload the asset.")
    return {
        "version": version, "tag": tag, "name": asset["name"],
        "url": asset["browser_download_url"], "sha256": digest[7:].lower(),
        "size": int(asset.get("size", 0)), "kind": expected_kind,
        "architecture": arch, "html_url": release.get("html_url", f"https://github.com/{UPDATE_REPOSITORY}/releases"),
    }


def download_verified(asset: dict, progress) -> Path:
    root = Path(os.environ.get("LOCALAPPDATA", Path.home() / "Library" / "Application Support")) / "ExeBuilderStudio" / "updates"
    root.mkdir(parents=True, exist_ok=True)
    filename = Path(asset["name"]).name
    if filename != asset["name"] or not filename.lower().endswith((".exe", ".dmg")):
        raise ValueError("Invalid installer filename in release metadata.")
    target = root / filename
    partial = root / (filename + ".part")
    digest = hashlib.sha256()
    try:
        _https(asset["url"])
        request = Request(asset["url"], headers={"User-Agent": "ExeBuilderStudio-Updater", "Accept-Encoding": "identity"})
        with _OPENER.open(request, timeout=45) as response, partial.open("wb") as output:
            _https(response.geturl())
            if "text/html" in response.headers.get("Content-Type", "").lower():
                raise ValueError("GitHub returned a web page instead of an installer.")
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
        if not partial.is_file() or partial.stat().st_size == 0 or (total and partial.stat().st_size != total):
            raise ValueError("The installer download is incomplete. Please try again.")
        if digest.hexdigest().lower() != asset["sha256"].lower():
            raise ValueError("SHA-256 verification failed. The installer was rejected.")
        if asset["kind"] == "exe":
            with partial.open("rb") as stream:
                if stream.read(2) != b"MZ":
                    raise ValueError("The downloaded file is not a valid Windows executable.")
        else:
            with partial.open("rb") as stream:
                stream.seek(-512, os.SEEK_END)
                if stream.read(4) != b"koly":
                    raise ValueError("The downloaded file is not a valid macOS DMG image.")
        partial.replace(target)
        return target
    except Exception:
        partial.unlink(missing_ok=True)
        raise


class _UpdateWorker(QThread):
    progress = Signal(int, int)
    completed = Signal(object)
    failed = Signal(str)

    def __init__(self, action: str, parent=None):
        super().__init__(parent)
        self.action = action

    def run(self):
        try:
            asset = current_platform_asset()
            asset["is_update"] = version_key(asset["version"]) > version_key(APP_VERSION)
            if not asset["is_update"]:
                self.completed.emit({"current": True, "asset": asset})
                return
            if self.action == "check":
                self.completed.emit({"update": True, "asset": asset})
                return
            path = download_verified(asset, self.progress)
            self.completed.emit({"downloaded": True, "asset": asset, "path": str(path)})
        except Exception as exc:
            self.failed.emit(str(exc))


class UniversalUpdateCard(QWidget):
    """One About-page updater UI, choosing EXE or architecture-matched DMG automatically."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.worker = None
        self.asset = None
        self.language = 0
        self.setObjectName("UniversalUpdateCard")
        layout = QVBoxLayout(self)
        self.title = QLabel()
        self.title.setStyleSheet("font-size: 16px; font-weight: 600;")
        layout.addWidget(self.title)
        self.status = QLabel()
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        row = QHBoxLayout()
        self.check_button = QPushButton()
        self.install_button = QPushButton()
        self.install_button.setEnabled(False)
        self.check_button.clicked.connect(lambda: self.start("check"))
        self.install_button.clicked.connect(lambda: self.start("download"))
        row.addWidget(self.check_button)
        row.addWidget(self.install_button)
        layout.addLayout(row)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)
        self.note = QLabel()
        self.note.setWordWrap(True)
        layout.addWidget(self.note)
        self.set_language(0)

    def set_language(self, index):
        self.language = max(0, min(2, int(index)))
        strings = {
            "title": ("ExeBuilderStudio Updates", "อัปเดต ExeBuilderStudio", "ExeBuilderStudio ဢပ်ႉတဵတ်ႉ"),
            "check": ("Check for Updates", "ตรวจสอบการอัปเดต", "ၸႅတ်ႈထတ်းဝႃးသျိၼ်းမႂ်ႇ"),
            "install": ("Download and Install Update", "ดาวน์โหลดและติดตั้งอัปเดต", "လူတ်ႇလႄႈဢိၼ်ႇသတေႃးဢပ်ႉတဵတ်ႉ"),
            "note": (
                "Downloads the latest stable release for this operating system. Windows uses the Setup EXE; macOS selects the DMG matching this Mac's architecture. SHA-256 is verified before launch. macOS opens the verified DMG for manual installation.",
                "ดาวน์โหลดรุ่นเสถียรล่าสุดให้ตรงกับระบบ: Windows ใช้ Setup EXE ส่วน macOS เลือก DMG ให้ตรงกับสถาปัตยกรรมเครื่อง และตรวจสอบ SHA-256 ก่อนเปิดไฟล์ โดย macOS จะเปิด DMG ให้ติดตั้งด้วยตนเอง",
                "ဝႃးသျိၼ်းမႂ်ႇတေၵိုင်ႇၵပ်း OS။ Windows ၸႂ်ႉ Setup EXE၊ macOS လိူၵ်ႈ DMG ႁႂ်ႈမႅၼ်ႈ architecture လႄႈၸႅတ်ႈထတ်း SHA-256။ macOS ပိုတ်ႇ DMG တႃႇဢိၼ်ႇသတေႃး"
            )
        }
        self.title.setText(strings["title"][self.language])
        self.check_button.setText(strings["check"][self.language])
        self.install_button.setText(strings["install"][self.language])
        self.note.setText(strings["note"][self.language])

    def start(self, action):
        if self.worker and self.worker.isRunning():
            return
        self.check_button.setEnabled(False)
        self.install_button.setEnabled(False)
        self.progress_bar.setRange(0, 0)
        self.progress_bar.show()
        self.status.setText("Checking GitHub Releases…" if action == "check" else "Downloading and verifying update…")
        self.worker = _UpdateWorker(action, self)
        self.worker.progress.connect(self.on_progress)
        self.worker.completed.connect(self.on_complete)
        self.worker.failed.connect(self.on_failed)
        self.worker.finished.connect(self.on_finished)
        self.worker.start()

    def on_progress(self, done, total):
        if total > 0:
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(min(100, int(done * 100 / total)))
            self.status.setText(f"Downloading update: {done / 1048576:.1f} / {total / 1048576:.1f} MB")
        else:
            self.progress_bar.setRange(0, 0)

    def on_complete(self, result):
        asset = result["asset"]
        self.asset = asset
        if result.get("current"):
            self.status.setText(f"You are up to date. Installed: {APP_VERSION}; latest: {asset['version']}.")
            QMessageBox.information(self, "No update available", self.status.text())
        elif result.get("update"):
            self.status.setText(f"Update available: {APP_VERSION} → {asset['version']} ({asset['kind'].upper()}, {asset['architecture']}).")
            QMessageBox.information(self, "Update available", f"ExeBuilderStudio {asset['version']} is available. Click Download and Install Update to continue.")
        elif result.get("downloaded"):
            path = Path(result["path"])
            self.status.setText(f"Downloaded and SHA-256 verified: {path}")
            if asset["kind"] == "exe":
                ok, _pid = QProcess.startDetached(str(path), [], str(path.parent))
                if not ok:
                    QMessageBox.warning(self, "Cannot start installer", f"The installer was verified but could not be started. Open it manually:\n{path}")
                    return
                QMessageBox.information(self, "Installer started", "The verified Windows installer has been started. ExeBuilderStudio will close so the installer can update the application.")
                from PySide6.QtWidgets import QApplication
                QApplication.instance().quit()
            else:
                QMessageBox.information(self, "Update downloaded", "The DMG was downloaded and SHA-256 verified. The disk image will open; quit ExeBuilderStudio, drag the new app into Applications, and choose Replace if asked.")
                if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(path))):
                    QMessageBox.warning(self, "Could not open DMG", f"Open this file manually:\n{path}")

    def on_failed(self, error):
        self.status.setText("Update failed: " + error)
        QMessageBox.warning(self, "ExeBuilderStudio update failed", error)

    def on_finished(self):
        self.check_button.setEnabled(True)
        self.progress_bar.hide()
        self.install_button.setEnabled(bool(self.asset and self.asset.get("is_update")))
        worker = self.worker
        self.worker = None
        if worker:
            worker.deleteLater()
