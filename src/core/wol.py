"""
Wake-on-LAN implementation.

This module provides Wake-on-LAN functionality to remotely power on
computers over the network using magic packets.
"""

from __future__ import annotations

import ipaddress
import socket
import time
from typing import TYPE_CHECKING

from src.core import logger
from src.core.network import ConnectionStatus, NetworkChecker
from src.core.validators import normalize_mac


if TYPE_CHECKING:
    from collections.abc import Callable

    ProgressCallback = Callable[[int, int, str, ConnectionStatus], None]


class WakeOnLAN:
    """Wake-on-LAN manager."""

    def __init__(
        self,
        mac_address: str,
        ip_address: str,
        check_ports: list[int] | None = None,
    ) -> None:
        """
        Initialize WakeOnLAN.

        Args:
            mac_address: Target PC MAC address
            ip_address: Target PC IP address
            check_ports: Ports to verify status (default: RPC, SMB, WinRM)

        Raises:
            ValueError: If MAC address is invalid
        """
        normalized = normalize_mac(mac_address)
        if not normalized:
            raise ValueError(f"Invalid MAC address: {mac_address}")

        self.mac_address = normalized
        self.ip_address = ip_address
        self.check_ports = check_ports or [135, 445, 5985]

    @staticmethod
    def _subnet_broadcast(ip: str, prefix_len: int = 24) -> str:
        """
        Derive subnet-directed broadcast address from an IP.

        Args:
            ip: Target IP address (e.g. "192.168.1.100")
            prefix_len: Subnet prefix length (default: 24)

        Returns:
            Broadcast address (e.g. "192.168.1.255")
        """
        network = ipaddress.IPv4Network(f"{ip}/{prefix_len}", strict=False)
        return str(network.broadcast_address)

    def send_magic_packet(self) -> bool:
        """
        Send Magic Packet to wake up the PC.

        Sends multiple packets to both subnet-directed and limited broadcast
        addresses on ports 7 and 9 for maximum reliability.

        Returns:
            True if at least one packet was sent successfully
        """
        try:
            # Remove separators and convert to bytes
            mac_clean = self.mac_address.replace("-", "").replace(":", "")
            mac_bytes = bytes.fromhex(mac_clean)

            # Create Magic Packet: 6 bytes FF + 16x MAC
            magic_packet = b"\xff" * 6 + mac_bytes * 16

            # Determine broadcast addresses
            subnet_broadcast = self._subnet_broadcast(self.ip_address)
            targets = [
                (subnet_broadcast, 9),
                (subnet_broadcast, 7),
                ("255.255.255.255", 9),
            ]

            sent_count = 0
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                for _repeat in range(3):
                    for addr, port in targets:
                        try:
                            sock.sendto(magic_packet, (addr, port))
                            sent_count += 1
                        except OSError as e:
                            logger.debug(f"Failed to send to {addr}:{port}: {e}")

            logger.info(
                f"Magic Packet sent to {self.mac_address} "
                f"({sent_count} packets, broadcast={subnet_broadcast})"
            )
            return sent_count > 0

        except Exception as e:
            logger.error(f"Error sending Magic Packet: {e}")
            return False

    def check_status(
        self, ping_timeout: int = 2000, port_timeout: int = 3000
    ) -> ConnectionStatus:
        """
        Check current PC status.

        Args:
            ping_timeout: Ping timeout in ms
            port_timeout: Port check timeout in ms

        Returns:
            Connection status object
        """
        return NetworkChecker.get_status(
            self.ip_address, self.check_ports, ping_timeout, port_timeout
        )

    def wake_and_wait(
        self,
        max_retries: int = 10,
        retry_interval: int = 15,
        progress_callback: ProgressCallback | None = None,
    ) -> tuple[bool, str]:
        """
        Wake the PC and wait until it's fully booted.

        Args:
            max_retries: Maximum number of attempts
            retry_interval: Interval between attempts in seconds
            progress_callback: Callback to report progress
                Signature: (attempt, max_attempts, message, status)

        Returns:
            Tuple of (success, message)
        """
        logger.info("=" * 50)
        logger.info("Starting Wake-on-LAN process")
        logger.info(f"Target: {self.ip_address} ({self.mac_address})")
        logger.info(f"Max attempts: {max_retries}")
        logger.info("=" * 50)

        # Check if already online
        initial_status = self.check_status()

        if initial_status.fully_booted:
            message = "PC de Áudio já está online e pronto"
            logger.info(message)
            if progress_callback:
                progress_callback(0, max_retries, message, initial_status)
            return True, message

        if initial_status.pingable:
            logger.info("Audio PC responds to ping, but still booting")

        # Retry loop
        for attempt in range(1, max_retries + 1):
            logger.info(f"--- Attempt {attempt}/{max_retries} ---")

            # Send Magic Packet
            if not self.send_magic_packet():
                logger.error("Failed to send Magic Packet")
                continue

            message = f"Magic Packet enviado (tentativa {attempt}/{max_retries})"
            if progress_callback:
                progress_callback(attempt, max_retries, message, initial_status)

            # Wait before checking
            wait_time = 20 if attempt == 1 else retry_interval
            logger.info(f"Waiting {wait_time}s before checking...")

            # Check periodically during wait
            for elapsed in range(wait_time):
                time.sleep(1)

                # Check every 5 seconds during wait
                if elapsed % 5 == 0 and elapsed > 0:
                    quick_status = self.check_status()

                    if quick_status.pingable:
                        logger.info("Ping detected during wait!")
                        message = "PC de Áudio detectado! Verificando se está pronto..."
                        if progress_callback:
                            progress_callback(
                                attempt, max_retries, message, quick_status
                            )
                        break

                    if progress_callback:
                        wait_msg = f"Aguardando resposta... ({elapsed}/{wait_time}s)"
                        progress_callback(attempt, max_retries, wait_msg, quick_status)

            # Full status check
            logger.info("Checking Audio PC status...")
            current_status = self.check_status()

            logger.info(
                f"Status: Ping={current_status.pingable}, "
                f"Ports open={current_status.ports_open}, "
                f"Ready={current_status.fully_booted}"
            )

            if current_status.fully_booted:
                message = "PC de Áudio está online e pronto!"
                logger.info(f"SUCCESS! {message}")
                if progress_callback:
                    progress_callback(attempt, max_retries, message, current_status)
                return True, message

            if current_status.pingable:
                # PC responded but not fully ready
                logger.info("PC responded to ping, waiting for system to load...")
                message = "PC ligado, aguardando sistema carregar..."

                # More frequent checks
                for sub_check in range(6):
                    time.sleep(5)
                    sub_status = self.check_status()

                    logger.debug(
                        f"Sub-check {sub_check + 1}/6: "
                        f"Ping={sub_status.pingable}, "
                        f"Ports={sub_status.ports_open}"
                    )

                    if progress_callback:
                        sub_msg = f"Sistema inicializando... ({sub_check + 1}/6)"
                        progress_callback(attempt, max_retries, sub_msg, sub_status)

                    if sub_status.fully_booted:
                        message = "PC de Áudio está online e pronto!"
                        logger.info(f"SUCCESS! {message}")
                        if progress_callback:
                            progress_callback(attempt, max_retries, message, sub_status)
                        return True, message
            else:
                logger.warning("PC did not respond. Trying again...")
                if progress_callback:
                    fail_msg = "PC não respondeu. Tentando novamente..."
                    progress_callback(attempt, max_retries, fail_msg, current_status)

        # Failed after all attempts
        final_status = self.check_status()
        message = f"Não foi possível ligar PC de Áudio após {max_retries} tentativas"
        logger.error(message)
        logger.error(f"Final status: {final_status.status_text}")

        if progress_callback:
            progress_callback(max_retries, max_retries, message, final_status)

        return False, message
