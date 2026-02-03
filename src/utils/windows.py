"""
Windows-specific utilities for system configuration.

This module provides Windows Task Scheduler and startup registry management
for automatic execution of the synchronization system.
"""

from __future__ import annotations

import contextlib
import os
import shutil
import subprocess
from pathlib import Path

from src.core import logger


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
    def create_shutdown_task(exe_path: str) -> tuple[bool, str]:
        """
        Create a scheduled task to run on shutdown/logoff.

        This task executes the Audio PC shutdown script.

        Args:
            exe_path: Full path to the shutdown executable

        Returns:
            Tuple of (success, message)
        """
        try:
            # Get current username
            current_user = os.getenv("USERNAME", "")

            # Task XML with shutdown trigger
            task_xml = f"""<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>Turns off the Audio PC when the OBS PC is shut down</Description>
    <Author>Church Stream Sync</Author>
  </RegistrationInfo>
  <Triggers>
    <SessionStateChangeTrigger>
      <Enabled>true</Enabled>
      <StateChange>SessionLogoff</StateChange>
      <UserId>{current_user}</UserId>
    </SessionStateChangeTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
      <UserId>{current_user}</UserId>
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>HighestAvailable</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <AllowHardTerminate>true</AllowHardTerminate>
    <StartWhenAvailable>false</StartWhenAvailable>
    <RunOnlyIfNetworkAvailable>false</RunOnlyIfNetworkAvailable>
    <IdleSettings>
      <StopOnIdleEnd>false</StopOnIdleEnd>
      <RestartOnIdle>false</RestartOnIdle>
    </IdleSettings>
    <AllowStartOnDemand>true</AllowStartOnDemand>
    <Enabled>true</Enabled>
    <Hidden>false</Hidden>
    <RunOnlyIfIdle>false</RunOnlyIfIdle>
    <WakeToRun>false</WakeToRun>
    <ExecutionTimeLimit>PT5M</ExecutionTimeLimit>
    <Priority>7</Priority>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>{exe_path}</Command>
    </Exec>
  </Actions>
</Task>"""

            # Save temporary XML
            temp_dir = os.getenv("TEMP", ".")
            temp_xml = Path(temp_dir) / "ChurchShutdownTask.xml"
            temp_xml.write_text(task_xml, encoding="utf-16")

            # Import task via schtasks
            ps_script = f'''
# Remove existing task if present
schtasks /Delete /TN "ChurchStreamShutdown" /F 2>$null

# Import new task
schtasks /Create /TN "ChurchStreamShutdown" /XML "{temp_xml}" /RU "{current_user}" /F
'''

            result = subprocess.run(
                ["powershell", "-Command", ps_script],
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )

            # Remove temporary file
            with contextlib.suppress(OSError):
                temp_xml.unlink()

            if result.returncode == 0 or "SUCCESS" in result.stdout:
                logger.info("Shutdown task created successfully")
                return True, "Tarefa de shutdown configurada"
            logger.warning(f"Possible error creating shutdown task: {result.stderr}")
            # Try alternative method
            return WindowsTaskManager._create_shutdown_task_alternative(exe_path)

        except Exception:
            logger.exception("Error creating shutdown task")
            return WindowsTaskManager._create_shutdown_task_alternative(exe_path)

    @staticmethod
    def _create_shutdown_task_alternative(exe_path: str) -> tuple[bool, str]:
        """
        Alternative method using Group Policy Scripts.

        Args:
            exe_path: Executable path

        Returns:
            Tuple of (success, message)
        """
        try:
            logger.info("Trying alternative method via Group Policy")

            # Create shutdown script via Group Policy
            system_root = os.getenv("SYSTEMROOT", r"C:\Windows")
            gpo_path = (
                Path(system_root)
                / "System32"
                / "GroupPolicy"
                / "User"
                / "Scripts"
                / "Logoff"
            )
            gpo_path.mkdir(parents=True, exist_ok=True)

            # Copy executable to GPO folder
            shutdown_exe = gpo_path / "ChurchShutdown.exe"
            shutil.copy2(exe_path, shutdown_exe)

            # Configure scripts.ini
            scripts_ini = gpo_path.parent / "scripts.ini"
            ini_content = f"""[Logoff]
0CmdLine={shutdown_exe.name}
0Parameters=
"""
            scripts_ini.write_text(ini_content, encoding="utf-8")

            # Update Group Policy
            subprocess.run(
                ["gpupdate", "/force"], capture_output=True, timeout=60, check=False
            )

            logger.info("Shutdown configured via Group Policy")
            return True, "Shutdown configurado via Group Policy"

        except Exception as e:
            logger.exception("Error in alternative method")
            return False, f"Erro: {e!s}"

    @staticmethod
    def remove_tasks() -> tuple[bool, str]:
        """
        Remove all tasks created by the system.

        Returns:
            Tuple of (success, message)
        """
        try:
            ps_script = """
# Remove tasks
Unregister-ScheduledTask -TaskName "ChurchStreamSync" -Confirm:$false -ErrorAction SilentlyContinue
Unregister-ScheduledTask -TaskName "ChurchStreamShutdown" -Confirm:$false -ErrorAction SilentlyContinue

# Remove GPO scripts
$gpoPath = "$env:SystemRoot\\System32\\GroupPolicy\\User\\Scripts\\Logoff"
if (Test-Path $gpoPath) {
    Remove-Item "$gpoPath\\ChurchShutdown.exe" -ErrorAction SilentlyContinue
    Remove-Item "$gpoPath\\..\\scripts.ini" -ErrorAction SilentlyContinue
}

gpupdate /force
"""

            subprocess.run(
                ["powershell", "-Command", ps_script],
                capture_output=True,
                timeout=60,
                check=False,
            )

            logger.info("Tasks removed successfully")
            return True, "Sistema desinstalado"

        except Exception as e:
            logger.exception("Error removing tasks")
            return False, str(e)

    @staticmethod
    def check_tasks() -> dict[str, bool | str | None]:
        """
        Check status of scheduled tasks.

        Returns:
            Dictionary with task status
        """
        status: dict[str, bool | str | None] = {
            "startup": False,
            "shutdown": False,
            "startup_details": None,
            "shutdown_details": None,
        }

        try:
            # Check startup task
            result = subprocess.run(
                ["schtasks", "/Query", "/TN", "ChurchStreamSync", "/FO", "LIST", "/V"],
                capture_output=True,
                text=True,
                check=False,
            )

            if result.returncode == 0:
                status["startup"] = True
                status["startup_details"] = result.stdout

            # Check shutdown task
            result = subprocess.run(
                [
                    "schtasks",
                    "/Query",
                    "/TN",
                    "ChurchStreamShutdown",
                    "/FO",
                    "LIST",
                    "/V",
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            if result.returncode == 0:
                status["shutdown"] = True
                status["shutdown_details"] = result.stdout

        except Exception as e:
            logger.error(f"Error checking tasks: {e}")

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
