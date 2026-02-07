"""
Build script for compiling executables.

This module uses PyInstaller to compile all application components
into standalone Windows executables.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import PyInstaller.__main__


# Directories
PROJECT_ROOT = Path(__file__).parent.parent
SRC_DIR = PROJECT_ROOT / "src"
DIST_DIR = PROJECT_ROOT / "dist"
BUILD_DIR = PROJECT_ROOT / "build"
RESOURCES_DIR = PROJECT_ROOT / "resources"


def clean_build_dirs() -> None:
    """Clean previous build directories."""
    print("Cleaning build directories...")

    if DIST_DIR.exists():
        shutil.rmtree(DIST_DIR)

    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR)

    DIST_DIR.mkdir(exist_ok=True)


def build_main_app() -> None:
    """Compile the main application (Wake on LAN)."""
    print("\n" + "=" * 60)
    print("Compiling ChurchStreamSync.exe...")
    print("=" * 60)

    args = [
        str(SRC_DIR / "main.py"),
        "--name=ChurchStreamSync",
        "--onefile",
        "--windowed",
        f"--distpath={DIST_DIR}",
        f"--workpath={BUILD_DIR}",
        "--clean",
        "--noupx",
        # Icon (if exists)
        # f"--icon={RESOURCES_DIR / 'icons' / 'app.ico'}",
        # Additional data
        "--add-data=src;src",
        # Hooks and hidden imports
        "--hidden-import=PyQt5",
        "--hidden-import=PyQt5.QtCore",
        "--hidden-import=PyQt5.QtGui",
        "--hidden-import=PyQt5.QtWidgets",
        "--hidden-import=wmi",
        "--hidden-import=win32api",
        "--hidden-import=win32com",
        # Settings
        "--noconfirm",
    ]

    PyInstaller.__main__.run(args)
    print("\n[OK] ChurchStreamSync.exe compiled successfully!")


# Note: ChurchShutdown.exe is no longer needed as shutdown is handled
# by the background service intercepting Windows shutdown events


def build_installer() -> None:
    """Compile the installer."""
    print("\n" + "=" * 60)
    print("Compiling ChurchSetup.exe...")
    print("=" * 60)

    args = [
        str(PROJECT_ROOT / "installer" / "setup.py"),
        "--name=ChurchSetup",
        "--onefile",
        "--windowed",
        f"--distpath={DIST_DIR}",
        f"--workpath={BUILD_DIR}",
        "--clean",
        "--noupx",
        # Additional data
        "--add-data=src;src",
        # Hooks and hidden imports
        "--hidden-import=PyQt5",
        "--hidden-import=PyQt5.QtCore",
        "--hidden-import=PyQt5.QtGui",
        "--hidden-import=PyQt5.QtWidgets",
        # Settings
        "--noconfirm",
    ]

    PyInstaller.__main__.run(args)
    print("\n[OK] ChurchSetup.exe compiled successfully!")


def build_uninstaller() -> None:
    """Compile the uninstaller."""
    print("\n" + "=" * 60)
    print("Compiling ChurchUninstall.exe...")
    print("=" * 60)

    args = [
        str(PROJECT_ROOT / "installer" / "uninstall.py"),
        "--name=ChurchUninstall",
        "--onefile",
        "--windowed",
        f"--distpath={DIST_DIR}",
        f"--workpath={BUILD_DIR}",
        "--clean",
        "--noupx",
        # Additional data
        "--add-data=src;src",
        # Hooks and hidden imports
        "--hidden-import=PyQt5",
        "--hidden-import=PyQt5.QtCore",
        "--hidden-import=PyQt5.QtGui",
        "--hidden-import=PyQt5.QtWidgets",
        # Settings
        "--noconfirm",
    ]

    PyInstaller.__main__.run(args)
    print("\n[OK] ChurchUninstall.exe compiled successfully!")


def create_readme() -> None:
    """Create README in dist folder."""
    readme_content = """
Church Stream Sync - Executables
==================================

FILES:
------
- ChurchSetup.exe     - Run this to configure the system (optional after first setup)
- ChurchStreamSync.exe - Main application (runs automatically on login)
- ChurchUninstall.exe  - Uninstaller

HOW IT WORKS:
-------------
The system now runs as a single executable in the background:
1. On login → Automatically wakes up the Audio PC
2. Runs in background (system tray icon)
3. On shutdown → Automatically shuts down the Audio PC

INSTALLATION:
-------------
1. Run ChurchSetup.exe
2. Follow the setup wizard
3. Enter the Audio PC information
4. Log off and log back in

The system will be activated automatically!

SYSTEM TRAY:
------------
Look for the Church Stream Sync icon in the system tray (near the clock).
Right-click for options:
- View Audio PC status
- Manually shutdown Audio PC
- Access configuration
- View logs
- Exit

SUPPORT:
--------
Logs: %APPDATA%\\ChurchStreamSync\\logs\\

For more information, see the full documentation.
"""

    readme_path = DIST_DIR / "README.txt"
    readme_path.write_text(readme_content, encoding="utf-8")
    print("\n[OK] README.txt created")


def main() -> None:
    """Main build function."""
    print("\n" + "=" * 60)
    print("Church Stream Sync - Build System")
    print("=" * 60)

    # Clean directories
    clean_build_dirs()

    # Compile all executables
    build_installer()
    build_uninstaller()
    build_main_app()

    # Create README
    create_readme()

    # Final summary
    print("\n" + "=" * 60)
    print("BUILD COMPLETED SUCCESSFULLY!")
    print("=" * 60)
    print(f"\nExecutables available at: {DIST_DIR}")
    print("\nGenerated files:")
    for exe in DIST_DIR.glob("*.exe"):
        print(f"  - {exe.name}")

    print("\n" + "=" * 60)
    print("NEXT STEPS:")
    print("  1. Copy executables to the OBS PC")
    print("  2. Run ChurchSetup.exe")
    print("  3. Configure the system")
    print("  4. Test with logoff/login")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
