"""
Audio PC shutdown script.

This module is automatically executed on OBS PC shutdown/logoff via Windows
Task Scheduler. It remotely shuts down the Audio PC using multiple fallback
methods.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import time
from pathlib import Path

# Prevent console window flash on Windows when running subprocess commands
_SUBPROCESS_FLAGS = getattr(subprocess, "CREATE_NO_WINDOW", 0)

from src.core import logger
from src.core.config import get_config
from src.core.network import NetworkChecker


class RemoteShutdown:
    """Remote shutdown manager with multiple fallback methods."""

    def __init__(self, ip_address: str, username: str, password: str) -> None:
        """
        Initialize shutdown manager.

        Args:
            ip_address: Target PC IP address
            username: Windows username
            password: Windows password
        """
        self.ip_address = ip_address
        self.username = username
        self.password = password

    def is_online(self) -> bool:
        """Check if the PC is online."""
        pingable, _ = NetworkChecker.ping(self.ip_address, timeout=1000)
        return pingable

    def shutdown_via_psexec(self) -> bool:
        """
        Shutdown using PsExec (if available).

        Supports accounts without password (pass empty string as password).

        Returns:
            True if successful
        """
        try:
            # Find PsExec in PATH or executable folder
            psexec = self._find_psexec()
            if not psexec:
                logger.warning("PsExec not found")
                return False

            # Build command - always pass credentials, empty string for no password
            command = [
                psexec,
                f"\\\\{self.ip_address}",
                "-u",
                self.username,
                "-p",
                self.password,  # Can be empty string for accounts without password
                "-d",
                "shutdown",
                "/s",
                "/f",
                "/t",
                "5",
            ]

            result = subprocess.run(
                command,
                capture_output=True,
                timeout=10,
                check=False,
                creationflags=_SUBPROCESS_FLAGS,
            )

            success = result.returncode == 0
            if success:
                logger.info("Shutdown sent via PsExec")

            return success

        except Exception as e:
            logger.error(f"Error using PsExec: {e}")
            return False

    def shutdown_via_wmi(self) -> bool:
        """
        Shutdown using WMI (Windows Management Instrumentation).

        Supports accounts without password (empty password string).

        Returns:
            True if successful
        """
        try:
            import wmi

            # Connect to remote PC - pass empty password for accounts without password
            connection = wmi.WMI(
                computer=self.ip_address,
                user=self.username,
                password=self.password,  # Can be empty string for passwordless accounts
            )

            # Execute shutdown
            os_list = connection.Win32_OperatingSystem()
            for os_obj in os_list:
                result = os_obj.Win32Shutdown(5)  # 5 = Forced shutdown

                if result == 0:
                    logger.info("Shutdown sent via WMI")
                    return True
                logger.warning(f"WMI returned code: {result}")
                return False

            return False

        except ImportError:
            logger.warning("WMI library not available")
            return False

        except Exception as e:
            logger.error(f"Error using WMI: {e}")
            return False

    def shutdown_via_powershell(self) -> bool:
        """
        Shutdown using PowerShell Remoting.

        Supports accounts without password (empty password string).

        Returns:
            True if successful
        """
        try:
            # PowerShell script - supports empty password for accounts without password
            # Convert empty string to secure string works for passwordless accounts
            ps_script = f"""
            $password = ConvertTo-SecureString '{self.password}' -AsPlainText -Force
            $credential = New-Object System.Management.Automation.PSCredential('{self.username}', $password)

            Invoke-Command -ComputerName {self.ip_address} -Credential $credential -ScriptBlock {{
                Stop-Computer -Force
            }} -ErrorAction Stop
            """

            # Execute PowerShell
            result = subprocess.run(
                ["powershell", "-Command", ps_script],
                capture_output=True,
                timeout=15,
                text=True,
                check=False,
                creationflags=_SUBPROCESS_FLAGS,
            )

            success = result.returncode == 0
            if success:
                logger.info("Shutdown sent via PowerShell")
            else:
                logger.warning(f"PowerShell failed: {result.stderr}")

            return success

        except Exception as e:
            logger.error(f"Error using PowerShell: {e}")
            return False

    def shutdown_via_net(self) -> bool:
        """
        Shutdown using 'net' and 'shutdown' commands.

        Supports accounts without password (pass empty string or "*" for no password).

        Returns:
            True if successful
        """
        try:
            # Establish IPC connection
            # For accounts without password, use "" or omit password
            if self.password:
                net_use = f"net use \\\\{self.ip_address}\\IPC$ /user:{self.username} {self.password}"
            else:
                # Use empty password for accounts without password
                net_use = (
                    f'net use \\\\{self.ip_address}\\IPC$ /user:{self.username} ""'
                )

            subprocess.run(
                net_use,
                shell=True,
                capture_output=True,
                timeout=5,
                check=False,
                creationflags=_SUBPROCESS_FLAGS,
            )

            # Send shutdown
            shutdown_cmd = f"shutdown /s /f /m \\\\{self.ip_address} /t 5"
            result = subprocess.run(
                shutdown_cmd,
                shell=True,
                capture_output=True,
                timeout=5,
                text=True,
                check=False,
                creationflags=_SUBPROCESS_FLAGS,
            )

            # Clean up connection
            time.sleep(1)
            subprocess.run(
                f"net use \\\\{self.ip_address}\\IPC$ /delete /yes",
                shell=True,
                capture_output=True,
                check=False,
                creationflags=_SUBPROCESS_FLAGS,
            )

            success = result.returncode == 0
            if success:
                logger.info("Shutdown sent via net/shutdown")

            return success

        except Exception as e:
            logger.error(f"Error using net/shutdown: {e}")
            return False

    def execute(self, expedited: bool = False) -> bool:
        """
        Execute shutdown with optional expedited mode.

        Args:
            expedited: If True, use shorter timeouts for faster shutdown

        Returns:
            True if successful
        """
        success, _ = self.shutdown(expedited=expedited)
        return success

    def shutdown(self, expedited: bool = False) -> tuple[bool, str]:
        """
        Attempt to shutdown the PC using multiple methods.

        Args:
            expedited: If True, use shorter timeouts (for system shutdown blocking)

        Returns:
            Tuple of (success, message)
        """
        logger.info("=" * 50)
        logger.info(f"Starting shutdown process (expedited={expedited})")
        logger.info(f"Target: {self.ip_address}")
        logger.info("=" * 50)

        # Check if already offline
        if not self.is_online():
            message = "PC de Áudio já está offline"
            logger.info(message)
            return True, message

        # Methods in order of preference
        methods = [
            ("PowerShell Remoting", self.shutdown_via_powershell),
            ("WMI", self.shutdown_via_wmi),
            ("Net/Shutdown", self.shutdown_via_net),
            ("PsExec", self.shutdown_via_psexec),
        ]

        # Adjust wait time based on mode
        max_wait = 30 if expedited else 60

        for method_name, method_func in methods:
            logger.info(f"Trying method: {method_name}")

            try:
                if method_func():
                    # Wait for confirmation
                    time.sleep(2 if expedited else 3)

                    if self._wait_for_shutdown(max_wait=max_wait):
                        message = f"PC de Áudio desligado via {method_name}"
                        logger.info(f"SUCCESS: {message}")
                        return True, message
                    logger.warning("Command sent but PC still online")

            except Exception as e:
                logger.error(f"Error in method {method_name}: {e}")

        # Failed all methods
        message = "Não foi possível desligar PC de Áudio"
        logger.error(message)
        return False, message

    def _wait_for_shutdown(self, max_wait: int = 60) -> bool:
        """
        Wait for shutdown confirmation.

        Args:
            max_wait: Maximum wait time in seconds

        Returns:
            True if PC shutdown confirmed
        """
        logger.info("Waiting for shutdown confirmation...")

        consecutive_offline = 0
        required_checks = 3

        for _i in range(max_wait):
            time.sleep(1)

            if not self.is_online():
                consecutive_offline += 1
                logger.debug(f"Offline check {consecutive_offline}/{required_checks}")

                if consecutive_offline >= required_checks:
                    logger.info("PC confirmed offline")
                    return True
            else:
                consecutive_offline = 0

        logger.warning(f"Timeout after {max_wait}s")
        return False

    def _find_psexec(self) -> str | None:
        """Find PsExec.exe in the system."""
        # Search in PATH
        psexec = shutil.which("psexec.exe")
        if psexec:
            return psexec

        # Search in executable folder
        exe_dir = Path(sys.executable).parent
        psexec_path = exe_dir / "psexec.exe"

        if psexec_path.exists():
            return str(psexec_path)

        return None


def main() -> None:
    """Main function."""
    try:
        logger.info("=" * 60)
        logger.info("Church Stream Sync - Shutdown")
        logger.info("=" * 60)

        # Load configuration
        config = get_config()

        if not config.is_configured():
            logger.error("System not configured!")
            sys.exit(1)

        logger.info(f"Audio PC: {config.audio_pc.name}")
        logger.info(f"IP: {config.audio_pc.ip_address}")

        # Execute shutdown
        shutdown_manager = RemoteShutdown(
            ip_address=config.audio_pc.ip_address,
            username=config.audio_pc.username,
            password=config.audio_pc.password,
        )

        success, _message = shutdown_manager.shutdown()

        # Show notification (if configured)
        if config.ui.show_notifications:
            from src.gui.notification import show_notification

            if success:
                show_notification(
                    "Sistema Encerrado", "PC de Áudio foi desligado", icon="info"
                )
            else:
                show_notification(
                    "Aviso", "Não foi possível desligar PC de Áudio", icon="warning"
                )

        logger.info("=" * 60)
        sys.exit(0 if success else 1)

    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(0)

    except Exception:
        logger.exception("Fatal error during shutdown")
        sys.exit(1)


if __name__ == "__main__":
    main()
