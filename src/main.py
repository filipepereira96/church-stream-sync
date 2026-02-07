"""
Main entry point for the system.

This module is automatically executed on user login via Windows Task Scheduler.
It routes execution to either:
- Setup mode: If configuration doesn't exist, shows setup wizard
- Service mode: If configuration exists, runs background service
"""

from __future__ import annotations

import os
import sys

from PyQt5.QtWidgets import QApplication, QMessageBox

from src.core import logger
from src.core.config import Config
from src.utils.windows import ensure_single_instance


def run_setup_mode() -> None:
    """
    Run the setup wizard to configure the application.

    After configuration is saved, the application will restart
    automatically in service mode.
    """
    logger.info("No configuration found, entering setup mode")

    try:
        from installer.setup import run_setup_wizard

        _ = QApplication(sys.argv)

        # Run setup wizard
        success = run_setup_wizard()

        if success:
            logger.info("Setup completed successfully, restarting in service mode...")

            # Restart application in service mode
            python = sys.executable
            os.execl(python, python, *sys.argv)
        else:
            logger.info("Setup cancelled by user")
            sys.exit(0)

    except Exception as e:
        logger.exception("Error during setup")

        try:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setWindowTitle("Erro no Instalador")
            msg.setText("Ocorreu um erro durante a configuração.")
            msg.setDetailedText(str(e))
            msg.setStandardButtons(QMessageBox.Ok)
            msg.exec_()
        except Exception:
            pass

        sys.exit(1)


def run_service_mode() -> None:
    """
    Run the background service.

    This mode:
    1. Sends WOL to Audio PC
    2. Runs continuously in background
    3. Intercepts Windows shutdown to manage Audio PC shutdown
    """
    logger.info("Configuration found, entering service mode")

    try:
        # Load and validate configuration
        config = Config.load()

        is_valid, error_message = config.validate()
        if not is_valid:
            logger.error(f"Invalid configuration: {error_message}")

            _ = QApplication(sys.argv)

            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setWindowTitle("Erro de Configuração")
            msg.setText("Configuração inválida detectada.")
            msg.setInformativeText(
                error_message + "\n\nExecute o instalador novamente."
            )
            msg.setStandardButtons(QMessageBox.Ok)
            msg.exec_()

            sys.exit(1)

        logger.info(f"Audio PC: {config.audio_pc.name}")
        logger.info(f"IP: {config.audio_pc.ip_address}")
        logger.info(f"MAC: {config.audio_pc.mac_address}")

        # Start background service
        from src.service.background import BackgroundService

        service = BackgroundService()
        service.start()

    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(0)

    except Exception as e:
        logger.exception("Fatal error during service execution")

        try:
            _ = QApplication(sys.argv)

            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setWindowTitle("Erro Fatal")
            msg.setText("Ocorreu um erro inesperado.")
            msg.setDetailedText(str(e))
            msg.setStandardButtons(QMessageBox.Ok)
            msg.exec_()
        except Exception:
            pass

        sys.exit(1)


def main() -> None:
    """
    Main entry point with mode routing.

    Decides whether to run setup wizard or background service based on
    configuration existence.
    """
    try:
        logger.info("=" * 60)
        logger.info("Church Stream Sync - Starting")
        logger.info("=" * 60)

        # Single instance check
        if not ensure_single_instance():
            logger.warning("Another instance is already running")

            _ = QApplication(sys.argv)

            msg = QMessageBox()
            msg.setIcon(QMessageBox.Information)
            msg.setWindowTitle("Já em Execução")
            msg.setText("Church Stream Sync já está rodando.")
            msg.setInformativeText(
                "Verifique o ícone na bandeja do sistema (system tray)."
            )
            msg.setStandardButtons(QMessageBox.Ok)
            msg.exec_()

            sys.exit(0)

        # Mode detection: check if config exists
        if not Config.exists():
            # No config -> Setup mode
            run_setup_mode()
        else:
            # Config exists -> Service mode
            run_service_mode()

    except Exception:
        logger.exception("Fatal error in main")
        sys.exit(1)


if __name__ == "__main__":
    main()
