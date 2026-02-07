"""
Background service module for Church Stream Sync.

This module contains the background service that runs continuously,
monitoring Windows shutdown events and managing the Audio PC lifecycle.
"""

from .background import BackgroundService, ShutdownHandler


__all__ = ["BackgroundService", "ShutdownHandler"]
