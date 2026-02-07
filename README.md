# Church Stream Sync

> Automatic synchronization system for live streaming infrastructure

[![Build Status](https://github.com/filipepereira96/church-stream-sync/workflows/Build%20Executables/badge.svg)](https://github.com/filipepereira96/church-stream-sync/actions)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python Version](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

## 📋 Overview

Church Stream Sync automatically synchronizes two computers used in live streaming:
- **Main PC**: Computer with OBS Studio (operator)
- **Audio PC**: Computer connected to the sound mixer via USB

### How It Works

```
Main PC Login → Audio PC turns on automatically → Runs in background (system tray)
Main PC Shutdown → Audio PC shuts down first → Windows shutdown proceeds
```

The system runs as a background service that intercepts Windows shutdown events, ensuring the Audio PC is safely shut down before the Main PC completes its shutdown sequence. This eliminates the need to manually turn on/off the second computer and guarantees proper shutdown order.

## ✨ Features

- ✅ **Background Service** runs continuously, intercepting Windows shutdown
- ✅ **System Tray Icon** for easy access and status monitoring
- ✅ **Automatic Wake-on-LAN** on user login
- ✅ **Guaranteed Shutdown Order** blocks Main PC shutdown until Audio PC is off
- ✅ **Graphical interface** with real-time visual feedback
- ✅ **Smart retry** with up to 10 automatic attempts
- ✅ **Multiple methods** for shutdown (4 strategies with fallback)
- ✅ **Graphical installer** with configuration wizard
- ✅ **Detailed logging** system for diagnostics
- ✅ **Zero dependencies** on PCs (standalone executables)

## 🚀 Quick Installation

### Prerequisites

**Audio PC (controlled):**
- Windows 10/11
- Wake-on-LAN enabled in BIOS
- PowerShell Remoting enabled
- Wired network connection

**Main PC (controller):**
- Windows 10/11
- Same network as Audio PC

### Step 1: Configure Audio PC

Run as Administrator on the Audio PC:

```powershell
# Enable PowerShell Remoting
Enable-PSRemoting -Force

# Configure firewall
New-NetFirewallRule -Name "WinRM-HTTP-In" `
    -DisplayName "Windows Remote Management (HTTP-In)" `
    -Enabled True -Direction Inbound -Protocol TCP -LocalPort 5985

# Get required information
Write-Host "IP Address:"
ipconfig | Select-String "IPv4"

Write-Host "`nMAC Address:"
Get-NetAdapter | Select-Object Name, MacAddress
```

**BIOS:** Enable Wake-on-LAN (see [detailed documentation](INSTALL.md#bios))

### Step 2: Install on Main PC

1. Download the [latest release](https://github.com/filipepereira96/church-stream-sync/releases)
2. Run `ChurchSetup.exe`
3. Follow the wizard:
   - Configure IP and MAC of Audio PC
   - Enter administrator credentials (password optional for accounts without password)
   - Test the connection
   - Finalize installation

The system will automatically start on next login and run in the background.

### Step 3: Test

1. Logout and login on the Main PC
2. A startup window shows the Audio PC boot progress
3. After completion, the system minimizes to the system tray
4. Look for the Church Stream Sync icon near the clock (system tray)
5. Right-click the icon to:
   - View Audio PC status (online/offline)
   - Manually shutdown Audio PC
   - Access configuration
   - View logs

## 📖 Documentation

- **[Complete Installation Guide](INSTALL.md)** - Detailed step-by-step configuration
- **[Operator Guide](USER_GUIDE.md)** - Manual for end users
- **[Troubleshooting](#-troubleshooting)** - Solutions for common problems

## 🔧 Development

### Environment Setup

```bash
# Clone the repository
git clone https://github.com/filipepereira96/church-stream-sync.git
cd church-stream-sync

# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows

# Install dependencies
uv sync
```

### Project Structure

```
church-stream-sync/
├── src/                    # Source code
│   ├── main.py            # Entry point with mode routing
│   ├── service/           # Background service
│   │   └── background.py  # Shutdown interception
│   ├── shutdown.py        # Remote shutdown logic
│   ├── core/              # Core logic (config, network, WOL)
│   ├── gui/               # Graphical interface (startup, tray, shutdown progress)
│   └── utils/             # Utilities (Windows tasks, validators)
├── installer/             # Installation system
├── build/                 # Build scripts
├── .github/workflows/     # CI/CD (GitHub Actions)
└── docs/                  # Additional documentation
```

### Build Executables

```bash
python src/build.py
```

Generates executables in `dist/`:
- `ChurchSetup.exe` - Setup wizard (run once or to reconfigure)
- `ChurchStreamSync.exe` - Main application (background service)
- `ChurchUninstall.exe` - Uninstaller

### Testing

```bash
# Run in development mode (opens setup wizard if no config, otherwise starts service)
python src/main.py

# Test remote shutdown directly
python -c "from src.shutdown import RemoteShutdown; s = RemoteShutdown('192.168.1.100', 'username', 'password'); print(s.execute())"
```

## 🐛 Troubleshooting

### Audio PC doesn't turn on

**Checklist:**
- ✓ Wake-on-LAN enabled in BIOS?
- ✓ Network card configured correctly?
- ✓ PC connected via cable (not WiFi)?
- ✓ PC connected to power?
- ✓ Correct MAC address?

**Manual test:**
```powershell
Test-Connection 192.168.1.100  # Audio PC IP
```

### Audio PC doesn't shut down

**Checklist:**
- ✓ PowerShell Remoting enabled?
- ✓ Correct credentials?
- ✓ Firewall allows port 5985?

**Manual test:**
```powershell
Test-WSMan -ComputerName 192.168.1.100
```

### Window doesn't appear

**Solution:**
```powershell
# Check scheduled task
Get-ScheduledTask -TaskName "ChurchStreamSync"

# Re-run installer if necessary
ChurchSetup.exe
```

### View Logs

```powershell
# Open logs folder
explorer "$env:APPDATA\ChurchStreamSync\logs"

# View last 50 lines
Get-Content "$env:APPDATA\ChurchStreamSync\logs\*.log" -Tail 50
```

### Accounts Without Password

The system supports connecting to user accounts without password configured:

- Leave the **password field empty** during setup
- Works with all shutdown methods (PowerShell, WMI, net, PsExec)
- Ideal for local accounts without password on Audio PC

**Note:** For security reasons, it's recommended to use password-protected accounts in production environments.

## 🤝 Contributing

Contributions are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

1. Fork the project
2. Create a branch for your feature (`git checkout -b feature/NewFeature`)
3. Commit your changes (`git commit -m 'Add NewFeature'`)
4. Push to the branch (`git push origin feature/NewFeature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Developed to simplify live streaming operations in churches
- Uses open-source technologies: Python, PyQt5, PyInstaller
- Inspired by the real needs of media teams

## 📊 Project Status

- ✅ **Functional:** All main features implemented
- ✅ **Tested:** In use in production environments
- ✅ **Documented:** Complete documentation available
- 🔄 **In development:** Continuous improvements

## 🗺️ Roadmap

- [ ] Support for multiple Audio PCs
- [ ] Web configuration interface
- [ ] Push notifications (Discord/Telegram)
- [ ] Statistics dashboard
- [ ] Linux/macOS support
- [ ] Automated tests (pytest)

## 💬 Support

- **Issues:** [GitHub Issues](https://github.com/filipepereira96/church-stream-sync/issues)
- **Discussions:** [GitHub Discussions](https://github.com/filipepereira96/church-stream-sync/discussions)
- **Wiki:** [Wiki Documentation](https://github.com/filipepereira96/church-stream-sync/wiki)

---

**Made with ❤️ for live streaming communities**
