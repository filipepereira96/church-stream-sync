"""
Startup window with visual feedback.

This module provides a PyQt5-based GUI window that shows the progress
of the Wake-on-LAN process with real-time status updates.
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from PyQt5.QtCore import Qt, QThread, QTimer, pyqtSignal
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.core import logger
from src.core.config import get_config
from src.core.wol import WakeOnLAN


if TYPE_CHECKING:
    from PyQt5.QtGui import QCloseEvent

    from src.core.network import ConnectionStatus


class WakeThread(QThread):
    """Thread to execute Wake-on-LAN without blocking the UI."""

    progress = pyqtSignal(int, int, str, object)  # attempt, max, message, status
    finished_signal = pyqtSignal(bool, str)  # success, message

    def __init__(self, wol: WakeOnLAN, max_retries: int, retry_interval: int) -> None:
        super().__init__()
        self.wol = wol
        self.max_retries = max_retries
        self.retry_interval = retry_interval

    def run(self) -> None:
        """Execute Wake-on-LAN in a separate thread."""
        try:
            success, message = self.wol.wake_and_wait(
                max_retries=self.max_retries,
                retry_interval=self.retry_interval,
                progress_callback=self._on_progress,
            )
            self.finished_signal.emit(success, message)
        except Exception as e:
            logger.exception("Error during Wake-on-LAN")
            self.finished_signal.emit(False, f"Erro: {e!s}")

    def _on_progress(
        self, attempt: int, max_attempts: int, message: str, status: ConnectionStatus
    ) -> None:
        """Progress callback."""
        self.progress.emit(attempt, max_attempts, message, status)


class StartupWindow(QWidget):
    """Startup window with visual feedback."""

    def __init__(self) -> None:
        super().__init__()
        self.config = get_config()
        self.wake_thread: WakeThread | None = None
        self.auto_close_timer: QTimer | None = None

        self._init_ui()
        self._start_wake_process()

    def _init_ui(self) -> None:
        """Initialize the user interface."""
        self.setWindowTitle("Sistema de Transmissão - Igreja")
        self.setFixedSize(550, 400)
        self.setWindowFlags(Qt.Window | Qt.WindowStaysOnTopHint)

        # Center on screen
        screen = QApplication.desktop().screenGeometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)

        # Main layout
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(30, 30, 30, 30)
        main_layout.setSpacing(20)

        # Large emoji icon
        self.icon_label = QLabel("🎙️")
        self.icon_label.setAlignment(Qt.AlignCenter)
        icon_font = QFont("Segoe UI Emoji", 60)
        self.icon_label.setFont(icon_font)
        main_layout.addWidget(self.icon_label)

        # Title
        title_label = QLabel("Sistema de Transmissão")
        title_label.setAlignment(Qt.AlignCenter)
        title_font = QFont("Segoe UI", 16, QFont.Bold)
        title_label.setFont(title_font)
        main_layout.addWidget(title_label)

        # Main status
        self.status_label = QLabel("Iniciando PC de Áudio...")
        self.status_label.setAlignment(Qt.AlignCenter)
        status_font = QFont("Segoe UI", 12, QFont.Bold)
        self.status_label.setFont(status_font)
        self.status_label.setStyleSheet("color: #0078D4;")
        main_layout.addWidget(self.status_label)

        # Details
        self.details_label = QLabel("Enviando sinal de inicialização...")
        self.details_label.setAlignment(Qt.AlignCenter)
        details_font = QFont("Segoe UI", 10)
        self.details_label.setFont(details_font)
        self.details_label.setStyleSheet("color: #666666;")
        main_layout.addWidget(self.details_label)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #E0E0E0;
                border-radius: 5px;
                text-align: center;
                background-color: #F5F5F5;
                height: 28px;
            }
            QProgressBar::chunk {
                background-color: #0078D4;
                border-radius: 3px;
            }
        """)
        main_layout.addWidget(self.progress_bar)

        # Attempt label
        self.attempt_label = QLabel("Tentativa 1 de 10")
        self.attempt_label.setAlignment(Qt.AlignCenter)
        attempt_font = QFont("Segoe UI", 9)
        self.attempt_label.setFont(attempt_font)
        self.attempt_label.setStyleSheet("color: #999999;")
        main_layout.addWidget(self.attempt_label)

        # Spacer
        main_layout.addStretch()

        # OK button (initially hidden)
        self.ok_button = QPushButton("OK")
        self.ok_button.setFont(QFont("Segoe UI", 10))
        self.ok_button.setFixedSize(120, 40)
        self.ok_button.setStyleSheet("""
            QPushButton {
                background-color: #0078D4;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 8px;
            }
            QPushButton:hover {
                background-color: #106EBE;
            }
            QPushButton:pressed {
                background-color: #005A9E;
            }
        """)
        self.ok_button.clicked.connect(self.close)
        self.ok_button.hide()

        # Button layout
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(self.ok_button)
        button_layout.addStretch()
        main_layout.addLayout(button_layout)

        self.setLayout(main_layout)

        # Window style
        self.setStyleSheet("""
            QWidget {
                background-color: white;
            }
        """)

    def _start_wake_process(self) -> None:
        """Start the Wake-on-LAN process."""
        try:
            # Create WoL instance
            wol = WakeOnLAN(
                mac_address=self.config.audio_pc.mac_address,
                ip_address=self.config.audio_pc.ip_address,
                check_ports=self.config.network.check_ports,
            )

            # Create and start thread
            self.wake_thread = WakeThread(
                wol, self.config.network.max_retries, self.config.network.retry_interval
            )

            self.wake_thread.progress.connect(self._on_progress)
            self.wake_thread.finished_signal.connect(self._on_finished)
            self.wake_thread.start()

        except Exception as e:
            logger.exception("Error starting Wake-on-LAN process")
            self._show_error(f"Erro ao iniciar: {e!s}")

    def _on_progress(
        self, attempt: int, max_attempts: int, message: str, status: ConnectionStatus
    ) -> None:
        """Update UI with progress."""
        # Update labels
        self.details_label.setText(message)
        self.attempt_label.setText(f"Tentativa {attempt} de {max_attempts}")

        # Update progress bar
        if status.fully_booted:
            progress = 100
        elif status.pingable and status.ports_open > 0:
            progress = 75 + (status.ports_open * 5)
        elif status.pingable:
            progress = 60
        else:
            progress = min((attempt / max_attempts) * 50, 50)

        self.progress_bar.setValue(int(progress))

        # Log
        logger.debug(f"Progress: {attempt}/{max_attempts} - {message}")

    def _on_finished(self, success: bool, message: str) -> None:
        """Called when process finishes."""
        if success:
            self._show_success(message)
        else:
            self._show_error(message)

    def _show_success(self, message: str) -> None:
        """Show success message."""
        self.icon_label.setText("✅")
        self.status_label.setText("PC de Áudio Pronto!")
        self.status_label.setStyleSheet("color: #107C10;")
        self.details_label.setText("Você já pode começar a transmissão")
        self.progress_bar.setValue(100)
        self.attempt_label.hide()
        self.ok_button.show()

        logger.info(f"Success: {message}")

        # Auto-close after delay
        if self.config.ui.auto_close_delay > 0:
            self.auto_close_timer = QTimer()
            self.auto_close_timer.timeout.connect(self.close)
            self.auto_close_timer.start(self.config.ui.auto_close_delay)

    def _show_error(self, message: str) -> None:
        """Show error message."""
        self.icon_label.setText("⚠️")
        self.status_label.setText("Não foi possível ligar PC de Áudio")
        self.status_label.setStyleSheet("color: #D83B01;")
        self.details_label.setText(message)
        self.details_label.setStyleSheet("color: #D83B01;")
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #FFE0E0;
                border-radius: 5px;
                text-align: center;
                background-color: #FFF0F0;
                height: 28px;
            }
            QProgressBar::chunk {
                background-color: #D83B01;
                border-radius: 3px;
            }
        """)
        self.attempt_label.hide()
        self.ok_button.show()
        self.ok_button.setText("Fechar")

        logger.error(f"Error: {message}")

    def closeEvent(self, event: QCloseEvent) -> None:
        """Called when window is closed."""
        # Stop timer if exists
        if self.auto_close_timer:
            self.auto_close_timer.stop()

        # Stop thread if still running
        if self.wake_thread and self.wake_thread.isRunning():
            self.wake_thread.terminate()
            self.wake_thread.wait()

        event.accept()


def show_startup_window() -> int:
    """
    Show the startup window.

    Returns:
        Application exit code
    """
    app = QApplication(sys.argv)
    app.setStyle("Fusion")  # Modern style

    window = StartupWindow()
    window.show()

    return app.exec_()
