"""
Network operations module.

This module provides network-related functionality including:
- Ping operations
- TCP port checking
- Connection status tracking
- Hostname resolution
"""

from __future__ import annotations

import platform
import re
import socket
import subprocess
from dataclasses import dataclass

from src.core import SUBPROCESS_FLAGS, logger


@dataclass
class ConnectionStatus:
    """Connection status with the Audio PC."""

    pingable: bool = False
    ports_open: int = 0
    latency_ms: float | None = None
    fully_booted: bool = False

    @property
    def is_online(self) -> bool:
        """Check if the PC is online."""
        return self.pingable or self.ports_open > 0

    @property
    def status_text(self) -> str:
        """Get descriptive status text (in Portuguese for UI)."""
        if self.fully_booted:
            return "Online e Pronto"
        if self.pingable and self.ports_open > 0:
            return "Inicializando..."
        if self.pingable:
            return "Ligando..."
        return "Offline"


class NetworkChecker:
    """Network connectivity checker."""

    @staticmethod
    def ping(host: str, timeout: int = 2000) -> tuple[bool, float | None]:
        """
        Execute ping to a host.

        Args:
            host: IP address or hostname
            timeout: Timeout in milliseconds

        Returns:
            Tuple of (success, latency_ms)
        """
        try:
            # Determine parameters based on OS
            param = "-n" if platform.system().lower() == "windows" else "-c"
            timeout_param = "-w" if platform.system().lower() == "windows" else "-W"
            timeout_value = (
                str(timeout)
                if platform.system().lower() == "windows"
                else str(timeout // 1000)
            )

            # Execute ping
            command = ["ping", param, "1", timeout_param, timeout_value, host]
            result = subprocess.run(
                command,
                capture_output=True,
                timeout=timeout / 1000 + 1,
                check=False,
                creationflags=SUBPROCESS_FLAGS,
            )

            success = result.returncode == 0

            # Try to extract latency
            latency = None
            if success:
                output = result.stdout.decode("utf-8", errors="ignore")
                # Search for time in ms
                match = re.search(r"time[=<](\d+)", output, re.IGNORECASE)
                if match:
                    latency = float(match.group(1))

            return success, latency

        except Exception as e:
            logger.error(f"Error executing ping to {host}: {e}")
            return False, None

    @staticmethod
    def check_port(host: str, port: int, timeout: int = 3000) -> bool:
        """
        Check if a TCP port is open.

        Args:
            host: IP address or hostname
            port: Port number
            timeout: Timeout in milliseconds

        Returns:
            True if the port is open
        """
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout / 1000)
            result = sock.connect_ex((host, port))
            sock.close()
            return result == 0

        except Exception as e:
            logger.debug(f"Error checking port {port} on {host}: {e}")
            return False

    @staticmethod
    def check_multiple_ports(host: str, ports: list[int], timeout: int = 3000) -> int:
        """
        Check multiple TCP ports.

        Args:
            host: IP address or hostname
            ports: List of ports to check
            timeout: Timeout in milliseconds per port

        Returns:
            Number of open ports
        """
        open_count = 0
        for port in ports:
            if NetworkChecker.check_port(host, port, timeout):
                open_count += 1
        return open_count

    @staticmethod
    def get_status(
        host: str, ports: list[int], ping_timeout: int = 2000, port_timeout: int = 3000
    ) -> ConnectionStatus:
        """
        Get complete connection status.

        Args:
            host: IP address or hostname
            ports: Ports to check
            ping_timeout: Ping timeout in ms
            port_timeout: Port timeout in ms

        Returns:
            Connection status object
        """
        status = ConnectionStatus()

        # Check ping
        pingable, latency = NetworkChecker.ping(host, ping_timeout)
        status.pingable = pingable
        status.latency_ms = latency

        # Check ports (only if ping works)
        if pingable:
            status.ports_open = NetworkChecker.check_multiple_ports(
                host, ports, port_timeout
            )

        # PC considered fully booted if ping OK and at least 2 ports open
        status.fully_booted = status.pingable and status.ports_open >= 2

        return status

    @staticmethod
    def resolve_hostname(hostname: str) -> str | None:
        """
        Resolve hostname to IP address.

        Args:
            hostname: Hostname to resolve

        Returns:
            IP address or None if resolution fails
        """
        try:
            return socket.gethostbyname(hostname)
        except socket.gaierror:
            return None
