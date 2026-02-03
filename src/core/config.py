"""
Configuration management system.

This module provides dataclass-based configuration with JSON persistence,
supporting multiple configuration sections for different aspects of the app.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class AudioPCConfig:
    """Audio PC configuration settings."""

    name: str = "PC Áudio"
    ip_address: str = ""
    mac_address: str = ""
    username: str = ""
    password: str = ""  # Optional - leave empty for accounts without password


@dataclass
class NetworkConfig:
    """Network and retry configuration settings."""

    max_retries: int = 10
    retry_interval: int = 15
    ping_timeout: int = 2000
    port_check_timeout: int = 3000
    check_ports: list[int] = field(default_factory=lambda: [135, 445, 5985])


@dataclass
class UIConfig:
    """User interface configuration settings."""

    show_startup_window: bool = True
    show_tray_icon: bool = True
    auto_close_delay: int = 3000  # ms
    show_notifications: bool = True
    theme: str = "modern"  # modern, classic


@dataclass
class LogConfig:
    """Logging configuration settings."""

    enabled: bool = True
    level: str = "INFO"  # DEBUG, INFO, WARNING, ERROR
    max_size_mb: int = 10
    backup_count: int = 5
    console_output: bool = False


class Config:
    """Main configuration class with singleton-like access."""

    CONFIG_DIR = Path(os.getenv("APPDATA", ".")) / "ChurchStreamSync"
    CONFIG_FILE = CONFIG_DIR / "config.json"

    def __init__(self) -> None:
        self.audio_pc = AudioPCConfig()
        self.network = NetworkConfig()
        self.ui = UIConfig()
        self.log = LogConfig()
        self._ensure_config_dir()

    def _ensure_config_dir(self) -> None:
        """Ensure configuration directory exists."""
        self.CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    def load(self) -> bool:
        """
        Load configuration from JSON file.

        Returns:
            True if loaded successfully, False otherwise
        """
        try:
            if not self.CONFIG_FILE.exists():
                return False

            with self.CONFIG_FILE.open(encoding="utf-8") as f:
                data = json.load(f)

            # Load each section
            if "audio_pc" in data:
                self.audio_pc = AudioPCConfig(**data["audio_pc"])

            if "network" in data:
                self.network = NetworkConfig(**data["network"])

            if "ui" in data:
                self.ui = UIConfig(**data["ui"])

            if "log" in data:
                self.log = LogConfig(**data["log"])

            return True

        except Exception as e:
            print(f"Error loading configuration: {e}")
            return False

    def save(self) -> bool:
        """
        Save configuration to JSON file.

        Returns:
            True if saved successfully, False otherwise
        """
        try:
            data = {
                "audio_pc": asdict(self.audio_pc),
                "network": asdict(self.network),
                "ui": asdict(self.ui),
                "log": asdict(self.log),
            }

            with self.CONFIG_FILE.open("w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)

            return True

        except Exception as e:
            print(f"Error saving configuration: {e}")
            return False

    def is_configured(self) -> bool:
        """
        Check if the system is configured.

        Returns:
            True if all required fields are set
        """
        return (
            bool(self.audio_pc.ip_address)
            and bool(self.audio_pc.mac_address)
            and bool(self.audio_pc.username)
        )

    def validate(self) -> tuple[bool, str | None]:  # noqa: PLR0911
        """
        Validate current configuration.

        Returns:
            Tuple of (is_valid, error_message)
        """
        from src.core.validators import validate_ip, validate_mac

        if not self.audio_pc.ip_address:
            return False, "Endereço IP não configurado"

        if not validate_ip(self.audio_pc.ip_address):
            return False, "Endereço IP inválido"

        if not self.audio_pc.mac_address:
            return False, "Endereço MAC não configurado"

        if not validate_mac(self.audio_pc.mac_address):
            return False, "Endereço MAC inválido"

        if not self.audio_pc.username:
            return False, "Usuário não configurado"

        # Password is optional - empty password uses Windows integrated auth
        return True, None

    @property
    def log_dir(self) -> Path:
        """Get log directory path."""
        log_path = self.CONFIG_DIR / "logs"
        log_path.mkdir(exist_ok=True)
        return log_path

    def to_dict(self) -> dict[str, Any]:
        """
        Convert configuration to dictionary.

        Returns:
            Dictionary representation of configuration
        """
        return {
            "audio_pc": asdict(self.audio_pc),
            "network": asdict(self.network),
            "ui": asdict(self.ui),
            "log": asdict(self.log),
        }


# Global configuration instance
_config: Config | None = None


def get_config() -> Config:
    """
    Return the global configuration instance.

    Returns:
        Singleton Config instance
    """
    global _config  # noqa: PLW0603
    if _config is None:
        _config = Config()
        _config.load()
    return _config


def reload_config() -> Config:
    """
    Reload configuration from file.

    Returns:
        Fresh Config instance
    """
    global _config  # noqa: PLW0603
    _config = Config()
    _config.load()
    return _config
