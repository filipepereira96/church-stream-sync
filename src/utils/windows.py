"""
Windows-specific utilities for system configuration.

This module provides Windows Task Scheduler and startup registry management
for automatic execution of the synchronization system.
"""

from __future__ import annotations

import subprocess

# Prevent console window flash on Windows when running subprocess commands
_SUBPROCESS_FLAGS = getattr(subprocess, "CREATE_NO_WINDOW", 0)

from src.core import logger


_mutex = None


class WindowsTaskManager:
    """Windows Task Scheduler manager."""

    @staticmethod
    def create_startup_task(exe_path: str) -> tuple[bool, str]:
        """
        Create a scheduled task to run on login.

        Args:
            exe_path: Full path to the executable

        Returns:
            Tuple of (success, message)
        """
        try:
            ps_script = f'''
$Action = New-ScheduledTaskAction -Execute "{exe_path}"
$Trigger = New-ScheduledTaskTrigger -AtLogon -User "$env:USERNAME"
$Principal = New-ScheduledTaskPrincipal -UserId "$env:USERNAME" -LogonType Interactive -RunLevel Highest
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable

# Remove existing task if present
Unregister-ScheduledTask -TaskName "ChurchStreamSync" -Confirm:$false -ErrorAction SilentlyContinue

# Create new task
Register-ScheduledTask -TaskName "ChurchStreamSync" -Action $Action -Trigger $Trigger -Principal $Principal -Settings $Settings -Force
'''

            result = subprocess.run(
                ["powershell", "-Command", ps_script],
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
                creationflags=_SUBPROCESS_FLAGS,
            )

            if result.returncode == 0:
                logger.info("Startup task created successfully")
                return True, "Tarefa de startup configurada"
            logger.error(f"Error creating startup task: {result.stderr}")
            return False, f"Erro: {result.stderr}"

        except Exception as e:
            logger.exception("Error creating startup task")
            return False, str(e)

    @staticmethod
    def remove_tasks() -> tuple[bool, str]:
        """
        Remove all tasks created by the system.

        Returns:
            Tuple of (success, message)
        """
        try:
            ps_script = """
Unregister-ScheduledTask -TaskName "ChurchStreamSync" -Confirm:$false -ErrorAction SilentlyContinue
"""

            subprocess.run(
                ["powershell", "-Command", ps_script],
                capture_output=True,
                timeout=30,
                check=False,
                creationflags=_SUBPROCESS_FLAGS,
            )

            logger.info("Task removed successfully")
            return True, "Sistema desinstalado"

        except Exception as e:
            logger.exception("Error removing task")
            return False, str(e)

    @staticmethod
    def check_tasks() -> dict[str, bool | str | None]:
        """
        Check status of scheduled task.

        Returns:
            Dictionary with task status
        """
        status: dict[str, bool | str | None] = {
            "startup": False,
            "startup_details": None,
        }

        try:
            result = subprocess.run(
                ["schtasks", "/Query", "/TN", "ChurchStreamSync", "/FO", "LIST", "/V"],
                capture_output=True,
                text=True,
                check=False,
                creationflags=_SUBPROCESS_FLAGS,
            )

            if result.returncode == 0:
                status["startup"] = True
                status["startup_details"] = result.stdout

        except Exception as e:
            logger.error(f"Error checking task: {e}")

        return status


class WindowsStartupManager:
    """Windows startup programs manager (registry-based)."""

    @staticmethod
    def add_to_startup(exe_path: str, name: str = "ChurchStreamSync") -> bool:
        """
        Add program to Windows startup registry.

        Args:
            exe_path: Executable path
            name: Registry entry name

        Returns:
            True if successful
        """
        try:
            import winreg

            key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE
            )
            winreg.SetValueEx(key, name, 0, winreg.REG_SZ, exe_path)
            winreg.CloseKey(key)

            logger.info(f"Added to startup: {name}")
            return True

        except Exception as e:
            logger.error(f"Error adding to startup: {e}")
            return False

    @staticmethod
    def remove_from_startup(name: str = "ChurchStreamSync") -> bool:
        """
        Remove program from startup registry.

        Args:
            name: Registry entry name

        Returns:
            True if successful
        """
        try:
            import winreg

            key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE
            )

            try:
                winreg.DeleteValue(key, name)
                logger.info(f"Removed from startup: {name}")
            except FileNotFoundError:
                pass

            winreg.CloseKey(key)
            return True

        except Exception as e:
            logger.error(f"Error removing from startup: {e}")
            return False


def ensure_single_instance() -> bool:
    """
    Ensure that only one instance of the application is running.

    Uses a Win32 mutex to detect if another instance is already active.

    Returns:
        True if this is the only instance, False if another instance is already running
    """
    global _mutex

    try:
        import win32api
        import win32event
        import winerror
    except ImportError:
        logger.warning("win32 modules not available, skipping single instance check")
        return True

    try:
        # Create a named mutex (None uses default security attributes)
        _mutex = win32event.CreateMutex(None, False, "ChurchStreamSyncMutex")  # pyright: ignore [reportArgumentType]

        # Check if mutex already exists
        last_error = win32api.GetLastError()

        if last_error == winerror.ERROR_ALREADY_EXISTS:
            logger.info("Another instance is already running")
            return False

        logger.info("Single instance check passed")
        return True

    except Exception as e:
        logger.error(f"Error checking single instance: {e}")
        # On error, allow execution to continue
        return True
