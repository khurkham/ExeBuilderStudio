#!/bin/bash
# Convenience launcher for building the native macOS distribution.
ROOT="$(cd "$(dirname "$0")" && pwd)"
exec /bin/bash "$ROOT/macos/build_macos_distribution.sh" "$@"
