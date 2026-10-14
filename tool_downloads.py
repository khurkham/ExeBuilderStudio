"""Backward-compatible import path for app.services.tool_downloads."""
import sys
from app.services import tool_downloads as _implementation
sys.modules[__name__] = _implementation
