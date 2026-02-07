"""
Background service module for continuous monitoring and shutdown interception.

This module contains the main background service that:
- Sends WOL to Audio PC on startup
- Runs continuously in background
- Intercepts Windows shutdown events
- Ensures Audio PC is shut down before allowing system shutdown
"""

from __future__ import annotations

import ctypes
import sys
import time
from ctypes import wintypes
from typing import TYPE_CHECKING

from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtWidgets import QApplication, QWidget

from src.core import logger
from src.core.config import Config
from src.core.network import NetworkChecker
from src.core.wol import WakeOnLAN


if TYPE_CHECKING:
    from src.gui.startup import StartupWindow
    from src.gui.tray import SystemTrayIcon


class ShutdownHandler(QWidget):
    """
    Handles Windows shutdown events and manages Audio PC shutdown.

    This widget intercepts WM_QUERYENDSESSION messages to block system
    shutdown until the Audio PC is confirmed to be offline.
    """

    shutdown_requested = pyqtSignal()

    def __init__(self, service: BackgroundService):
        """
        Initialize the shutdown handler.

        Args:
            service: Reference to the parent BackgroundService
        """
        super().__init__()
        self.service = service
        self.is_shutting_down = False

        # Load Windows DLLs for shutdown blocking
        try:
            self.user32 = ctypes.windll.user32
            self.user32.ShutdownBlockReasonCreate.argtypes = [
                wintypes.HWND,
                wintypes.LPCWSTR,
            ]
            self.user32.ShutdownBlockReasonCreate.restype = wintypes.BOOL
            self.user32.ShutdownBlockReasonDestroy.argtypes = [wintypes.HWND]
            self.user32.ShutdownBlockReasonDestroy.restype = wintypes.BOOL
            logger.info("Windows shutdown APIs loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load Windows shutdown APIs: {e}")
            self.user32 = None

    def nativeEvent(self, eventType: bytes, message: int) -> tuple[bool, int]:
        """
        Handle native Windows events.

        Intercepts WM_QUERYENDSESSION to block shutdown temporarily.

        Args:
            eventType: Type of event
            message: Message pointer

        Returns:
            Tuple of (handled, result)
        """
        if eventType == b"windows_generic_MSG":
            try:
                msg = wintypes.MSG.from_address(int(message))

                # WM_QUERYENDSESSION = 0x0011
                if msg.message == 0x0011:
                    logger.info("Windows shutdown event detected (WM_QUERYENDSESSION)")

                    if not self.is_shutting_down:
                        self.is_shutting_down = True
                        self.shutdown_requested.emit()

                    # Block shutdown temporarily
                    return True, 0

            except Exception as e:
                logger.error(f"Error handling native event: {e}")

        return False, 0

    def block_shutdown(self, reason: str = "Desligando PC de Áudio...") -> bool:
        """
        Block Windows shutdown with a visible reason.

        Args:
            reason: Reason to display to the user

        Returns:
            True if blocked successfully
        """
        if not self.user32:
            logger.warning("Cannot block shutdown: Windows APIs not available")
            return False

        try:
            hwnd = int(self.winId())
            result = self.user32.ShutdownBlockReasonCreate(hwnd, reason)

            if result:
                logger.info(f"Shutdown blocked: {reason}")
                return True
            logger.error("Failed to block shutdown")
            return False

        except Exception as e:
            logger.error(f"Error blocking shutdown: {e}")
            return False

    def unblock_shutdown(self) -> bool:
        """
        Remove shutdown block to allow Windows to continue.

        Returns:
            True if unblocked successfully
        """
        if not self.user32:
            return False

        try:
            hwnd = int(self.winId())
            result = self.user32.ShutdownBlockReasonDestroy(hwnd)

            if result:
                logger.info("Shutdown unblocked")
                return True
            logger.error("Failed to unblock shutdown")
            return False

        except Exception as e:
            logger.error(f"Error unblocking shutdown: {e}")
            return False


class WakeThread(QThread):
    """Thread for executing WOL operation without blocking UI."""

    progress = pyqtSignal(dict)
    finished = pyqtSignal(bool)

    def __init__(self, config: Config):
        """
        Initialize WOL thread.

        Args:
            config: Application configuration
        """
        super().__init__()
        self.config = config

    def run(self):
        """Execute WOL and wait for Audio PC to boot."""
        try:
            wol = WakeOnLAN(
                mac_address=self.config.audio_pc.mac_address,
                ip_address=self.config.audio_pc.ip_address,
                check_ports=self.config.network.check_ports,
            )

            # Progress callback for UI updates
            def on_progress(
                attempt: int, max_attempts: int, message: str, status: object
            ) -> None:
                self.progress.emit(
                    {
                        "attempt": attempt,
                        "max_attempts": max_attempts,
                        "message": message,
                        "status": status,
                    }
                )

            success, _ = wol.wake_and_wait(
                max_retries=self.config.network.max_retries,
                retry_interval=self.config.network.retry_interval,
                progress_callback=on_progress,
            )
            self.finished.emit(success)

        except Exception:
            logger.exception("Error during WOL operation")
            self.finished.emit(False)


class BackgroundService:
    """
    Main background service that manages the entire Audio PC lifecycle.

    This service:
    1. Sends WOL on startup
    2. Monitors system status
    3. Intercepts shutdown and manages Audio PC shutdown
    4. Runs continuously until system shutdown
    """

    def __init__(self):
        """Initialize the background service."""
        self.config = Config.load()
        self.app = QApplication.instance() or QApplication(sys.argv)
        self.shutdown_handler: ShutdownHandler | None = None
        self.tray_icon: SystemTrayIcon | None = None
        self.startup_window: StartupWindow | None = None

        logger.info("BackgroundService initialized")

    def start(self):
        """
        Start the background service.

        This method:
        1. Sends WOL to Audio PC
        2. Shows startup progress window (if enabled)
        3. Minimizes to system tray
        4. Enters Qt event loop (runs indefinitely)
        """
        logger.info("Starting background service...")

        # Prevent Qt from quitting when the last window (StartupWindow) closes.
        # The app must keep running in background with the system tray icon.
        self.app.setQuitOnLastWindowClosed(False)

        # Set process shutdown parameters (shutdown late in the sequence)
        try:
            kernel32 = ctypes.windll.kernel32
            kernel32.SetProcessShutdownParameters(0x3FF, 0)
            logger.info("Process shutdown parameters set")
        except Exception as e:
            logger.warning(f"Could not set shutdown parameters: {e}")

        # Initialize shutdown handler
        self.shutdown_handler = ShutdownHandler(self)
        self.shutdown_handler.shutdown_requested.connect(self._on_shutdown_requested)

        # Send WOL
        self._send_wol()

        # Initialize system tray
        from src.gui.tray import SystemTrayIcon

        self.tray_icon = SystemTrayIcon(self)
        self.tray_icon.show()

        logger.info("Background service started, entering event loop")

        # Enter Qt event loop (blocks until app exits)
        sys.exit(self.app.exec_())

    def _send_wol(self):
        """Send WOL packet and show progress window if enabled."""
        logger.info("Sending WOL to Audio PC...")

        # Check if we should show startup window
        show_window = self.config.ui.show_startup_window

        if show_window:
            # Import here to avoid circular dependency
            from src.gui.startup import StartupWindow

            self.startup_window = StartupWindow()
            self.startup_window.closed.connect(self._on_wol_finished)
            self.startup_window.show()
        else:
            # Silent mode - just send WOL without UI
            wol_thread = WakeThread(self.config)
            wol_thread.finished.connect(self._on_wol_finished)
            wol_thread.start()

    def _on_wol_finished(self, success: bool):
        """
        Handle WOL completion.

        Args:
            success: Whether WOL was successful
        """
        if success:
            logger.info("WOL completed successfully, Audio PC is online")
        else:
            logger.warning("WOL failed or timed out")

        # Clean up startup window reference if it exists
        if self.startup_window:
            self.startup_window.deleteLater()
            self.startup_window = None

    def _on_shutdown_requested(self):
        """Handle Windows shutdown request."""
        logger.info("Processing shutdown request...")

        # Block shutdown
        if self.shutdown_handler:
            self.shutdown_handler.block_shutdown("Desligando PC de Áudio...")

        # Show progress window
        from src.gui.shutdown_progress import ShutdownProgressWindow

        progress_window = ShutdownProgressWindow()
        progress_window.show()
        progress_window.start_progress()

        try:
            # Execute Audio PC shutdown
            success = self._shutdown_audio_pc(progress_window)

            # Update window with result
            progress_window.set_complete(success)

        finally:
            # Always unblock shutdown
            if self.shutdown_handler:
                self.shutdown_handler.unblock_shutdown()

            logger.info("Allowing Windows shutdown to proceed")
            time.sleep(1)
            self.app.quit()

    def _shutdown_audio_pc(self, progress_window=None) -> bool:
        """
        Shutdown the Audio PC with timeout protection.

        This method will attempt to shut down the Audio PC and wait
        for confirmation, but will not block Windows shutdown for more
        than 60 seconds.

        Args:
            progress_window: Optional progress window to update

        Returns:
            True if shutdown was successful
        """
        MAX_TIMEOUT = 60  # seconds
        start_time = time.time()

        logger.info("Starting Audio PC shutdown sequence...")

        try:
            # Quick check: is Audio PC already offline?
            if progress_window:
                progress_window.update_status("Verificando status do PC de áudio...")

            checker = NetworkChecker()
            status = checker.get_status(
                self.config.audio_pc.ip_address,
                ports=self.config.network.check_ports,
                ping_timeout=2000,
            )

            if not status.is_online:
                logger.info("Audio PC is already offline, skipping shutdown")
                if progress_window:
                    progress_window.update_status("PC de áudio já está offline")
                return True

            # Import shutdown module
            from src.shutdown import RemoteShutdown

            if progress_window:
                progress_window.update_status("Enviando comando de desligamento...")

            # Create shutdown instance
            shutdown = RemoteShutdown(
                ip_address=self.config.audio_pc.ip_address,
                username=self.config.audio_pc.username,
                password=self.config.audio_pc.password,
            )

            # Execute shutdown with expedited mode (shorter timeouts)
            success = shutdown.execute(expedited=True)

            if success:
                logger.info("Audio PC shutdown completed successfully")
                if progress_window:
                    progress_window.update_status("PC de áudio desligado!")
                return True

            # If first attempt failed, wait and verify shutdown
            if progress_window:
                progress_window.update_status(
                    "Aguardando confirmação de desligamento..."
                )

            while time.time() - start_time < MAX_TIMEOUT:
                time.sleep(2)

                status = checker.get_status(
                    self.config.audio_pc.ip_address,
                    ports=self.config.network.check_ports,
                    ping_timeout=2000,
                )

                if not status.is_online:
                    logger.info("Audio PC confirmed offline")
                    if progress_window:
                        progress_window.update_status("PC de áudio confirmado offline")
                    return True

            logger.warning(
                f"Audio PC shutdown timeout after {MAX_TIMEOUT}s, "
                "allowing system shutdown anyway"
            )
            if progress_window:
                progress_window.update_status("Timeout - permitindo desligamento")
            return False

        except Exception as e:
            logger.exception(f"Error during Audio PC shutdown: {e}")
            logger.warning("Allowing system shutdown despite error")
            if progress_window:
                progress_window.update_status(f"Erro: {e}")
            return False
