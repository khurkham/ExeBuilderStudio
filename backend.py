"""Backward-compatible import path for the build helpers in app.core.backend."""
import sys
from app.core import backend as _implementation
sys.modules[__name__] = _implementation
