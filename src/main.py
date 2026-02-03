"""
Main entry point for the system.

This module is automatically executed on user login via Windows Task Scheduler.
It initializes the Wake-on-LAN process to turn on the Audio PC.
"""

from __future__ import annotations

import sys

from src.core import logger
from src.core.config import get_config
from src.gui.startup import show_startup_window


def check_configuration() -> bool:
    """
    Check if the system is properly configured.

    Returns:
        True if configured, False otherwise
    """
    config = get_config()

    if not config.is_configured():
        logger.error("System is not configured!")

        # Try to show configuration message
        from PyQt5.QtWidgets import QApplication, QMessageBox

        app = QApplication(sys.argv)

        msg = QMessageBox()
        msg.setIcon(QMessageBox.Warning)
        msg.setWindowTitle("Configuração Necessária")
        msg.setText("O sistema de sincronização não está configurado.")
        msg.setInformativeText("Execute o instalador 'ChurchSetup.exe' primeiro.")
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec_()

        return False

    # Validate configuration
    is_valid, error_message = config.validate()
    if not is_valid:
        logger.error(f"Invalid configuration: {error_message}")

        from PyQt5.QtWidgets import QApplication, QMessageBox

        app = QApplication(sys.argv)  # noqa: F841

        msg = QMessageBox()
        msg.setIcon(QMessageBox.Critical)
        msg.setWindowTitle("Erro de Configuração")
        msg.setText("Configuração inválida detectada.")
        msg.setInformativeText(error_message)
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec_()

        return False

    return True


def main() -> None:
    """Main function."""
    try:
        logger.info("=" * 60)
        logger.info("Church Stream Sync - Initialization")
        logger.info("=" * 60)

        # Check configuration
        if not check_configuration():
            logger.error("Exiting due to configuration error")
            sys.exit(1)

        config = get_config()
        logger.info(f"Audio PC: {config.audio_pc.name}")
        logger.info(f"IP: {config.audio_pc.ip_address}")
        logger.info(f"MAC: {config.audio_pc.mac_address}")

        # Show startup window
        if config.ui.show_startup_window:
            logger.info("Showing startup window")
            exit_code = show_startup_window()
            logger.info(f"Window closed with code: {exit_code}")
            sys.exit(exit_code)
        else:
            # Silent mode (log only)
            logger.info("Running in silent mode")

            from src.core.wol import WakeOnLAN

            wol = WakeOnLAN(
                mac_address=config.audio_pc.mac_address,
                ip_address=config.audio_pc.ip_address,
                check_ports=config.network.check_ports,
            )

            success, message = wol.wake_and_wait(
                max_retries=config.network.max_retries,
                retry_interval=config.network.retry_interval,
            )

            if success:
                logger.info(f"SUCCESS: {message}")
                sys.exit(0)
            else:
                logger.error(f"FAILURE: {message}")
                sys.exit(1)

    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(0)

    except Exception as e:
        logger.exception("Fatal error during execution")

        # Try to show error message
        try:
            from PyQt5.QtWidgets import QApplication, QMessageBox

            app = QApplication(sys.argv)  # noqa: F841

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


if __name__ == "__main__":
    main()
