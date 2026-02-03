"""
Input validators for configuration data.

This module provides validation functions for various input types:
- IPv4 addresses
- MAC addresses
- Port numbers
- Hostnames
- Windows usernames
"""

from __future__ import annotations

import re


def validate_ip(ip: str) -> bool:
    """
    Validate an IPv4 address.

    Args:
        ip: IP address to validate

    Returns:
        True if valid, False otherwise
    """
    if not ip:
        return False

    pattern = r"^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$"
    match = re.match(pattern, ip)

    if not match:
        return False

    # Verify each octet is between 0-255
    return all(0 <= int(octet) <= 255 for octet in match.groups())


def validate_mac(mac: str) -> bool:
    """
    Validate a MAC address.

    Accepts formats: XX:XX:XX:XX:XX:XX or XX-XX-XX-XX-XX-XX or XXXXXXXXXXXX

    Args:
        mac: MAC address to validate

    Returns:
        True if valid, False otherwise
    """
    if not mac:
        return False

    # Remove whitespace
    mac = mac.strip()

    # Accepted patterns
    patterns = [
        r"^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$",  # XX:XX... or XX-XX...
        r"^([0-9A-Fa-f]{12})$",  # XXXXXXXXXXXX
    ]

    return any(re.match(pattern, mac) for pattern in patterns)


def normalize_mac(mac: str) -> str | None:
    """
    Normalize MAC address to standard format (XX-XX-XX-XX-XX-XX).

    Args:
        mac: MAC address to normalize

    Returns:
        Normalized MAC or None if invalid
    """
    if not validate_mac(mac):
        return None

    # Remove separators
    clean_mac = mac.replace(":", "").replace("-", "").upper()

    # Format with hyphens
    return "-".join(clean_mac[i : i + 2] for i in range(0, 12, 2))


def validate_port(port: int) -> bool:
    """
    Validate a port number.

    Args:
        port: Port number

    Returns:
        True if valid, False otherwise
    """
    return 1 <= port <= 65535


def validate_hostname(hostname: str) -> bool:
    """
    Validate a hostname.

    Args:
        hostname: Hostname to validate

    Returns:
        True if valid, False otherwise
    """
    if not hostname or len(hostname) > 253:
        return False

    # Hostname can contain letters, numbers, hyphens, and dots
    pattern = r"^[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$"
    return bool(re.match(pattern, hostname))


def validate_username(username: str) -> bool:
    """
    Validate a Windows username.

    Args:
        username: Username to validate

    Returns:
        True if valid, False otherwise
    """
    if not username or len(username) > 20:
        return False

    # Characters not allowed in Windows usernames
    invalid_chars = r'["/\[\]:;|=,+*?<>]'

    return not re.search(invalid_chars, username)
