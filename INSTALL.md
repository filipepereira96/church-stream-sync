# 📦 Complete Installation Guide

## Estimated time: 10-15 minutes

---

## 📋 Prerequisites

### Hardware
- Two Windows 10/11 computers
- Wired network connection between PCs
- Network card with Wake-on-LAN support

### Permissions
- Administrative access on both PCs
- Ability to modify BIOS settings

---

## Phase 1: Configure Audio PC (5 minutes)

### 1.1 Configure BIOS

1. **Restart the PC** and enter BIOS (usually DEL, F2, or F10)

2. **Navigate to Power Management** (or APM Configuration)

3. **Enable the following options:**
   - Wake on LAN
   - Power On by PCI-E
   - PME Event Wake Up
   - Resume by PCI-E Device

4. **Save and exit** (usually F10)

### 1.2 Configure Network Card in Windows

1. Open **Device Manager** (Win + X → Device Manager)

2. Expand **Network adapters**

3. Right-click your network card → **Properties**

4. On the **Power Management** tab:
   ```
   ☑ Allow this device to wake the computer
   ☑ Only allow a magic packet to wake the computer
   ```

5. On the **Advanced** tab, configure:
   ```
   Wake on Magic Packet: Enabled
   Wake on pattern match: Enabled (if available)
   ```

6. Click **OK** and restart the PC

### 1.3 Enable PowerShell Remoting

Run as **Administrator** on the Audio PC:

```powershell
# Enable PowerShell Remoting
Enable-PSRemoting -Force

# Configure script execution
Set-ExecutionPolicy RemoteSigned -Force

# Configure TrustedHosts (replace with Main PC IP)
Set-Item WSMan:\localhost\Client\TrustedHosts -Value "192.168.1.10" -Force

# Restart WinRM service
Restart-Service WinRM
```

### 1.4 Configure Firewall

```powershell
# Create rule for WinRM
New-NetFirewallRule -Name "WinRM-HTTP-In" `
    -DisplayName "Windows Remote Management (HTTP-In)" `
    -Enabled True `
    -Direction Inbound `
    -Protocol TCP `
    -LocalPort 5985

# Verify port is open
Test-NetConnection -ComputerName localhost -Port 5985
```

### 1.5 Get Required Information

```powershell
# IP Address
Write-Host "IP Address:" -ForegroundColor Cyan
ipconfig | Select-String "IPv4"

# MAC Address
Write-Host "`nMAC Address:" -ForegroundColor Cyan
Get-NetAdapter | Select-Object Name, MacAddress

# Write down this information to use in the installer
```

---

## Phase 2: Download and Prepare Executables (2 minutes)

### Option A: Download from Release

1. Go to [Releases](https://github.com/filipepereira96/church-stream-sync/releases)
2. Download the latest version (`church-stream-sync-vX.X.X.zip`)
3. Extract to a folder (e.g., `C:\ChurchStreamSync\`)

### Option B: Build from Source

```bash
# Clone the repository
git clone https://github.com/filipepereira96/church-stream-sync.git
cd church-stream-sync

# Create virtual environment
python -m venv venv
venv\Scripts\activate

# Install dependencies
uv sync

# Build
python src/build.py

# Executables will be in: dist/
```

---

## Phase 3: Install on Main PC (3 minutes)

### 3.1 Run Installer

1. On the Main PC, run **`ChurchSetup.exe`** as Administrator

2. **Page 1 - Welcome**
   - Read the introduction
   - Click **Next**

3. **Page 2 - Audio PC Configuration**

   Fill in the fields:
   ```
   Name: Audio PC (or descriptive name)
   IP: 192.168.1.100 (obtained in Phase 1)
   MAC: 00-11-22-33-44-55 (obtained in Phase 1)
   Username: Administrator (user with admin privileges)
   Password: ********* (optional - leave empty if account has no password)
   ```

   **Note:** The password field is optional. Leave it empty if the Audio PC user account doesn't have a password configured.

   - Click **Test Connection** to validate
   - If OK ✅ → **Next**
   - If error ❌ → Check settings

4. **Page 3 - Advanced Settings** (optional)
   ```
   Max retries: 10 (default)
   Interval: 15 seconds (default)
   ☑ Show window on startup
   ☑ Show notifications
   ```

   - Click **Next**

5. **Page 4 - Summary**
   - Review all settings
   - Click **Finish**

### 3.2 What the Installer Configures

The installer automatically:
- ✅ Saves settings in `%APPDATA%\ChurchStreamSync\`
- ✅ Creates **startup** scheduled task (runs on login)
- ✅ Configures logs in `%APPDATA%\ChurchStreamSync\logs\`

**Note:** The system now runs as a single background service that automatically handles both startup (WOL) and shutdown. No separate shutdown task is needed.

---

## Phase 4: Validate Installation (1-2 minutes)

### 4.1 Check Scheduled Task

```powershell
# Check task
Get-ScheduledTask -TaskName "ChurchStreamSync"

# Should show:
# TaskName: ChurchStreamSync
# State: Ready
# Triggers: At log on
```

### 4.2 Startup Test (Wake-on-LAN)

1. **Logout** from the Main PC
2. **Login** again
3. **Wait** for the startup window to appear:
   ```
   ╔════════════════════════════╗
   ║        🎙️                 ║
   ║ Ligando PC de Áudio...     ║
   ║ [████████░░░░] 60%         ║
   ╚════════════════════════════╝
   ```
4. **Confirm**: "✅ PC de Áudio Pronto!"
5. **Check** for the system tray icon near the clock
6. **Right-click** the icon to see the menu

**If it worked:** ✅ Installation successful!

### 4.3 Shutdown Test

1. **Make sure** Audio PC is on
2. **Initiate shutdown** on the Main PC (Start → Shutdown)
3. A **progress window should appear**: "Desligando PC de Áudio..."
4. Windows shutdown will be **temporarily blocked** (30-60 seconds)
5. After Audio PC confirms offline, **Windows will proceed** with shutdown

**If it worked:** ✅ System fully operational!

**Note:** The system now intercepts Windows shutdown events, ensuring the Audio PC shuts down first before allowing the Main PC to complete its shutdown sequence.

---

## 🔍 Configuration Verification

### Audio PC Checklist
- [x] Wake-on-LAN enabled in BIOS
- [x] Network card configured (Power Management)
- [x] PowerShell Remoting enabled (`Enable-PSRemoting`)
- [x] Firewall configured (port 5985)
- [x] Wired network connection
- [x] PC connected to power

### Main PC Checklist
- [x] Executables downloaded/built
- [x] `ChurchSetup.exe` executed successfully
- [x] Connection test passed ✅
- [x] Scheduled task created (ChurchStreamSync)
- [x] Login test worked (WOL + system tray icon appears)
- [x] Shutdown test worked (blocks until Audio PC is off)

---

## 🛠️ Advanced Configuration

### Adjust Retry Parameters

Edit the configuration in: `%APPDATA%\ChurchStreamSync\config.json`

```json
{
  "network": {
    "max_retries": 15,        // Increase attempts
    "retry_interval": 20      // Increase interval
  }
}
```

Or re-run the installer with new values.

### Configure Static IP (Recommended)

On the Audio PC, configure a fixed IP or DHCP reservation to avoid IP changes:

```powershell
# View current configuration
Get-NetIPAddress -InterfaceAlias "Ethernet"

# Configure static IP (example)
New-NetIPAddress -InterfaceAlias "Ethernet" `
    -IPAddress 192.168.1.100 `
    -PrefixLength 24 `
    -DefaultGateway 192.168.1.1
```

### Using Accounts Without Password

The system supports connecting to user accounts that don't have a password configured:

**Setup:**
1. During installation, leave the **Password field empty**
2. The system will connect using an empty password
3. All shutdown methods support this (PowerShell, WMI, net, PsExec)

**Requirements:**
- Audio PC must have a user account without password
- Account must have administrator privileges
- PowerShell Remoting must be enabled

**Security Considerations:**
- Accounts without password are less secure
- Recommended only for isolated/trusted networks
- Consider using password-protected accounts in production

---

## 🔧 Manual Configuration (If Installer Fails)

### Create Startup Task Manually

```powershell
# Run as Administrator
$exePath = "C:\ChurchStreamSync\ChurchStreamSync.exe"

$Action = New-ScheduledTaskAction -Execute $exePath
$Trigger = New-ScheduledTaskTrigger -AtLogon -User "$env:USERNAME"
$Principal = New-ScheduledTaskPrincipal -UserId "$env:USERNAME" `
    -LogonType Interactive -RunLevel Highest
$Settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Seconds 0)

Register-ScheduledTask -TaskName "ChurchStreamSync" `
    -Action $Action -Trigger $Trigger `
    -Principal $Principal -Settings $Settings -Force
```

**Note:** Only one task is needed now. The application runs in the background and automatically handles both startup (WOL) and shutdown (intercepts Windows shutdown events).

---

## 📊 Created Files and Folders

After installation, the following files are created:

```
%APPDATA%\ChurchStreamSync\
├── config.json           # System settings
└── logs\
    └── church_sync_YYYYMMDD.log  # Daily logs
```

**Task Scheduler:**
- Task Name: `ChurchStreamSync`
- Trigger: At logon
- Action: Run `ChurchStreamSync.exe`

---

## 🔄 Update

To update to a new version:

1. **Uninstall** the current version:
   ```
   ChurchUninstall.exe
   ```

2. **Download** the new version

3. **Run** the installer again:
   ```
   ChurchSetup.exe
   ```

Previous settings are preserved (if desired).

---

## 🗑️ Uninstallation

### Option 1: Use Uninstaller

```
ChurchUninstall.exe
```

### Option 2: Manual

```powershell
# Remove scheduled task
Unregister-ScheduledTask -TaskName "ChurchStreamSync" -Confirm:$false

# Remove settings
Remove-Item "$env:APPDATA\ChurchStreamSync" -Recurse -Force

# Remove executables (optional)
Remove-Item "C:\ChurchStreamSync" -Recurse -Force
```

---

## 📞 Getting Help

If you encounter problems:

1. **Check the [Troubleshooting](README.md#-troubleshooting)**
2. **Verify the [logs](#view-logs)**
3. **Open an [issue on GitHub](https://github.com/filipepereira96/church-stream-sync/issues)**

---

**Installation completed successfully!** 🎉

Now you can operate streaming without worrying about manually turning the Audio PC on/off.
