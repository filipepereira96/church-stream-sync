"""
Utilities module for Church Stream Sync.

This module contains platform-specific utilities:
- Windows Task Scheduler management
- Windows startup registry management
"""

from src.utils import windows


__all__ = ["windows"]
