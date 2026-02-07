"""
Shutdown progress window with visual feedback.

This module provides a PyQt5-based GUI window that shows the progress
of the Audio PC shutdown process during Windows shutdown.
"""

from __future__ import annotations

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QApplication,
    QDialog,
    QLabel,
    QProgressBar,
    QVBoxLayout,
)

from src.core import logger


class ShutdownProgressWindow(QDialog):
    """
    Progress window shown during Audio PC shutdown.

    Displays a modal window with progress bar to inform the user
    that the system is shutting down the Audio PC before allowing
    Windows shutdown to proceed.
    """

    def __init__(self):
        """Initialize the shutdown progress window."""
        super().__init__()

        self.progress_value = 0
        self.timer = QTimer()
        self.timer.timeout.connect(self._update_progress)

        self._init_ui()

        logger.info("Shutdown progress window created")

    def _init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("Desligando Sistema")
        self.setFixedSize(500, 300)
        self.setWindowFlags(
            Qt.Dialog | Qt.WindowStaysOnTopHint | Qt.CustomizeWindowHint
        )
        self.setModal(True)

        screen = QApplication.desktop().screenGeometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(40, 40, 40, 40)
        main_layout.setSpacing(25)

        icon_label = QLabel("⚠️")
        icon_label.setAlignment(Qt.AlignCenter)
        icon_font = QFont("Segoe UI Emoji", 50)
        icon_label.setFont(icon_font)
        main_layout.addWidget(icon_label)

        title_label = QLabel("Desligando PC de Áudio")
        title_label.setAlignment(Qt.AlignCenter)
        title_font = QFont("Segoe UI", 16, QFont.Bold)
        title_label.setFont(title_font)
        main_layout.addWidget(title_label)

        self.status_label = QLabel("Aguarde, desligando PC de áudio...")
        self.status_label.setAlignment(Qt.AlignCenter)
        status_font = QFont("Segoe UI", 10)
        self.status_label.setFont(status_font)
        self.status_label.setStyleSheet("color: #666;")
        main_layout.addWidget(self.status_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet(
            """
            QProgressBar {
                border: 2px solid #ddd;
                border-radius: 5px;
                background-color: #f0f0f0;
                height: 25px;
            }
            QProgressBar::chunk {
                background-color: #ff9800;
                border-radius: 3px;
            }
            """
        )
        main_layout.addWidget(self.progress_bar)

        info_label = QLabel(
            "O Windows será desligado assim que o PC de áudio for desligado."
        )
        info_label.setAlignment(Qt.AlignCenter)
        info_label.setWordWrap(True)
        info_font = QFont("Segoe UI", 9)
        info_label.setFont(info_font)
        info_label.setStyleSheet("color: #999;")
        main_layout.addWidget(info_label)

        main_layout.addStretch()
        self.setLayout(main_layout)

    def start_progress(self):
        """Start the progress animation."""
        logger.info("Starting shutdown progress animation")
        self.progress_value = 0
        self.progress_bar.setValue(0)
        self.timer.start(200)

    def stop_progress(self):
        """Stop the progress animation."""
        logger.info("Stopping shutdown progress animation")
        self.timer.stop()

    def _update_progress(self):
        """Update progress bar with animation."""
        self.progress_value = (self.progress_value + 2) % 100
        self.progress_bar.setValue(self.progress_value)

    def update_status(self, message: str):
        """
        Update status message.

        Args:
            message: Status message to display
        """
        logger.debug(f"Shutdown progress: {message}")
        self.status_label.setText(message)

    def set_complete(self, success: bool = True):
        """
        Set completion state.

        Args:
            success: Whether shutdown was successful
        """
        self.timer.stop()
        self.progress_bar.setValue(100)

        if success:
            self.status_label.setText("PC de áudio desligado com sucesso!")
            self.status_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
        else:
            self.status_label.setText("Permitindo desligamento...")
            self.status_label.setStyleSheet("color: #ff9800; font-weight: bold;")

        QTimer.singleShot(1000, self.close)

    def closeEvent(self, event):
        """Handle close event."""
        self.stop_progress()
        logger.info("Shutdown progress window closed")
        super().closeEvent(event)
