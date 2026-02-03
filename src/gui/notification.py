"""
Windows toast notification system.

This module provides Windows toast notifications with a fallback
to PyQt5 system tray notifications when win10toast is not available.
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from PyQt5.QtWidgets import QApplication, QSystemTrayIcon


def show_notification(
    title: str, message: str, icon: str = "info", duration: int = 3000
) -> bool:
    """
    Show a Windows toast notification.

    Args:
        title: Notification title
        message: Notification message
        icon: Icon type (info, warning, error)
        duration: Duration in milliseconds

    Returns:
        True if notification was displayed
    """
    try:
        # Try using win10toast (if available)
        try:
            from win10toast import ToastNotifier

            toaster = ToastNotifier()

            toaster.show_toast(
                title,
                message,
                duration=duration // 1000,  # Convert to seconds
                threaded=False,
            )

            return True

        except ImportError:
            # Fallback to PyQt5 if win10toast not available
            return _show_qt_notification(title, message, icon, duration)

    except Exception as e:
        print(f"Error showing notification: {e}")
        return False


def _show_qt_notification(title: str, message: str, icon: str, duration: int) -> bool:
    """
    Show notification using PyQt5 system tray.

    Args:
        title: Notification title
        message: Notification message
        icon: Icon type (info, warning, error)
        duration: Duration in milliseconds

    Returns:
        True if notification was displayed
    """
    try:
        from PyQt5.QtCore import QTimer
        from PyQt5.QtWidgets import QApplication, QSystemTrayIcon

        # Create temporary application if none exists
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)

        # Create tray icon
        tray = QSystemTrayIcon()

        # Set icon (use system default icon)
        icon_obj = tray.style().standardIcon(tray.style().SP_MessageBoxInformation)
        tray.setIcon(icon_obj)
        tray.setVisible(True)

        # Map message type
        icon_type = {
            "info": QSystemTrayIcon.Information,
            "warning": QSystemTrayIcon.Warning,
            "error": QSystemTrayIcon.Critical,
        }.get(icon, QSystemTrayIcon.Information)

        # Show notification
        tray.showMessage(title, message, icon_type, duration)

        # Timer to cleanup
        timer = QTimer()
        timer.timeout.connect(lambda: _cleanup_tray(tray, app))
        timer.start(duration + 500)

        return True

    except Exception as e:
        print(f"Error showing Qt notification: {e}")
        return False


def _cleanup_tray(tray: QSystemTrayIcon, app: QApplication) -> None:
    """
    Clean up tray icon after displaying notification.

    Args:
        tray: The system tray icon to clean up
        app: The application instance
    """
    try:
        tray.hide()
        tray.deleteLater()
        # Don't close app if it's an existing instance
        from PyQt5.QtWidgets import QApplication

        if QApplication.instance() == app:
            app.quit()
    except Exception:
        pass


# Alias for compatibility
def show_toast(
    title: str, message: str, icon: str = "info", duration: int = 3000
) -> bool:
    """
    Alias for show_notification.

    Args:
        title: Notification title
        message: Notification message
        icon: Icon type (info, warning, error)
        duration: Duration in milliseconds

    Returns:
        True if notification was displayed
    """
    return show_notification(title, message, icon=icon, duration=duration)
