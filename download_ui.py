"""Backward-compatible import path for app.ui.download_ui."""
import sys
from app.ui import download_ui as _implementation
sys.modules[__name__] = _implementation
