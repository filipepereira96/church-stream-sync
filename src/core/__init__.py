"""
Core module for Church Stream Sync.

This module contains the core functionality including:
- Configuration management
- Logging system
- Network operations (ping, port checking)
- Wake-on-LAN implementation
- Input validation
"""

import subprocess

# Prevent console window flash on Windows when running subprocess commands.
# On Windows, CREATE_NO_WINDOW (0x08000000) suppresses the console window.
# On other platforms, this resolves to 0 (no-op).
SUBPROCESS_FLAGS = getattr(subprocess, "CREATE_NO_WINDOW", 0)

from src.core import config, logger, network, validators, wol


__all__ = ["SUBPROCESS_FLAGS", "config", "logger", "network", "validators", "wol"]
