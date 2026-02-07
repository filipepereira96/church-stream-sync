"""
System tray icon module for background service.

Provides a persistent system tray icon with menu options for:
- Viewing Audio PC status
- Manual shutdown
- Accessing configuration
- Viewing logs
- Exiting the application
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import (
    QAction,
    QMenu,
    QMessageBox,
    QSystemTrayIcon,
)

from src.core import logger
from src.core.network import NetworkChecker


if TYPE_CHECKING:
    from src.service.background import BackgroundService


class SystemTrayIcon(QSystemTrayIcon):
    """
    System tray icon for the background service.

    Provides user awareness and control options while the service
    runs in the background.
    """

    def __init__(self, service: BackgroundService):
        """
        Initialize the system tray icon.

        Args:
            service: Reference to the BackgroundService
        """
        super().__init__()

        self.service = service
        self.config = service.config

        # Status check timer
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self._update_status)
        self.status_timer.start(30000)  # Update every 30 seconds

        # Current status
        self.audio_pc_online = False
        self.audio_pc_latency = 0

        # Setup icon and menu
        self._setup_icon()
        self._create_menu()

        # Initial status update
        self._update_status()

        logger.info("System tray icon initialized")

    def _setup_icon(self):
        """Setup the tray icon."""
        # Try to use a microphone icon if available, otherwise use default
        # In production, we'll embed an icon in the executable
        try:
            # For now, use Qt's default icon
            from PyQt5.QtWidgets import QStyle

            app = self.service.app
            icon = app.style().standardIcon(QStyle.SP_ComputerIcon)
            self.setIcon(icon)
        except Exception as e:
            logger.warning(f"Could not set tray icon: {e}")

        self.setToolTip("Church Stream Sync")

    def _create_menu(self):
        """Create the system tray menu."""
        menu = QMenu()

        # Status action (will be updated dynamically)
        self.status_action = QAction("🟡 Verificando status...", menu)
        self.status_action.setEnabled(False)
        menu.addAction(self.status_action)

        menu.addSeparator()

        # Shutdown Audio PC action
        shutdown_action = QAction("🔌 Desligar PC de Áudio Agora", menu)
        shutdown_action.triggered.connect(self._shutdown_audio_pc_now)
        menu.addAction(shutdown_action)

        # Configuration action
        config_action = QAction("⚙️  Configurações", menu)
        config_action.triggered.connect(self._open_configuration)
        menu.addAction(config_action)

        # View logs action
        logs_action = QAction("📄 Ver Logs", menu)
        logs_action.triggered.connect(self._open_logs)
        menu.addAction(logs_action)

        menu.addSeparator()

        # Exit action
        exit_action = QAction("❌ Sair", menu)
        exit_action.triggered.connect(self._on_exit)
        menu.addAction(exit_action)

        self.setContextMenu(menu)

    def _update_status(self):
        """Update Audio PC status in the menu."""
        try:
            checker = NetworkChecker()
            status = checker.get_status(
                self.config.audio_pc.ip_address,
                ports=self.config.network.check_ports,
                ping_timeout=2000,
            )

            self.audio_pc_online = status.is_online
            self.audio_pc_latency = status.latency_ms or 0

            if status.is_online:
                status_text = f"🟢 PC de Áudio: Online ({status.latency_ms}ms)"
                self.setToolTip("Church Stream Sync\nPC de Áudio: Online")
            else:
                status_text = "🔴 PC de Áudio: Offline"
                self.setToolTip("Church Stream Sync\nPC de Áudio: Offline")

            self.status_action.setText(status_text)

        except Exception as e:
            logger.error(f"Error updating status: {e}")
            self.status_action.setText("🟡 PC de Áudio: Status desconhecido")

    def _shutdown_audio_pc_now(self):
        """Shutdown the Audio PC immediately (manual trigger)."""
        logger.info("Manual shutdown requested from tray menu")

        # Confirm with user
        reply = QMessageBox.question(
            None,
            "Desligar PC de Áudio",
            "Tem certeza que deseja desligar o PC de Áudio agora?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if reply == QMessageBox.Yes:
            try:
                from src.shutdown import RemoteShutdown

                shutdown = RemoteShutdown(
                    ip_address=self.config.audio_pc.ip_address,
                    username=self.config.audio_pc.username,
                    password=self.config.audio_pc.password,
                )

                # Show message
                self.showMessage(
                    "Church Stream Sync",
                    "Desligando PC de Áudio...",
                    QSystemTrayIcon.Information,
                    3000,
                )

                success = shutdown.execute(expedited=True)

                if success:
                    logger.info("Manual shutdown completed successfully")
                    self.showMessage(
                        "Church Stream Sync",
                        "PC de Áudio desligado com sucesso!",
                        QSystemTrayIcon.Information,
                        3000,
                    )
                else:
                    logger.warning("Manual shutdown failed")
                    self.showMessage(
                        "Church Stream Sync",
                        "Falha ao desligar PC de Áudio. Verifique os logs.",
                        QSystemTrayIcon.Warning,
                        5000,
                    )

                # Update status immediately
                self._update_status()

            except Exception as e:
                logger.exception("Error during manual shutdown")
                QMessageBox.critical(
                    None,
                    "Erro",
                    f"Erro ao desligar PC de Áudio:\n{e!s}",
                )

    def _open_configuration(self):
        """Open the setup wizard to edit configuration."""
        logger.info("Opening configuration wizard from tray menu")

        try:
            from installer.setup import SetupWizard

            wizard = SetupWizard()

            # Pre-fill with current configuration
            # (The wizard should detect existing config and show edit mode)

            result = wizard.exec_()

            if result == SetupWizard.Accepted:
                logger.info("Configuration updated, restarting service...")

                # Show message
                self.showMessage(
                    "Church Stream Sync",
                    "Configuração atualizada! Reiniciando...",
                    QSystemTrayIcon.Information,
                    3000,
                )

                # Restart the application
                import sys

                python = sys.executable
                os.execl(python, python, *sys.argv)

        except Exception as e:
            logger.exception("Error opening configuration")
            QMessageBox.critical(
                None,
                "Erro",
                f"Erro ao abrir configurações:\n{e!s}",
            )

    def _open_logs(self):
        """Open the logs directory in Windows Explorer."""
        logger.info("Opening logs directory from tray menu")

        try:
            log_dir = self.config.log_dir

            if log_dir.exists():
                # Open in Explorer
                os.startfile(log_dir)
            else:
                QMessageBox.information(
                    None,
                    "Logs",
                    f"Diretório de logs não encontrado:\n{log_dir}",
                )

        except Exception as e:
            logger.exception("Error opening logs directory")
            QMessageBox.critical(
                None,
                "Erro",
                f"Erro ao abrir pasta de logs:\n{e!s}",
            )

    def _on_exit(self):
        """Handle exit request."""
        logger.info("Exit requested from tray menu")

        # Confirm with user
        reply = QMessageBox.question(
            None,
            "Sair",
            "Tem certeza que deseja sair?\n\n"
            "O PC de Áudio não será mais gerenciado automaticamente.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if reply == QMessageBox.Yes:
            logger.info("User confirmed exit, shutting down service")

            # Stop status timer
            self.status_timer.stop()

            # Hide tray icon
            self.hide()

            # Quit application
            self.service.app.quit()
