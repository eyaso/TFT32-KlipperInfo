# TFT32 Moonraker Plugin

![Version](https://img.shields.io/badge/Version-1.1.0-blue.svg)
![Build](https://img.shields.io/badge/Build-PASSED-brightgreen.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)
![Platform](https://img.shields.io/badge/Platform-Raspberry%20Pi-red.svg)

**Display-only TFT integration for Klipper/Moonraker**

This plugin enables TFT32 displays (MKS, BIGTREETECH) to show real-time printer information from Klipper via Moonraker. The TFT acts as a display-only device showing temperatures, print progress, and status updates.

## 📊 Current Status

- **Version**: 1.1.0
- **Build Status**: ✅ PASSED
- **Last Updated**: January 25, 2025
- **Testing**: Verified with BIGTREETECH TFT32 on Raspberry Pi 3/4
- **Compatibility**: Moonraker, Klipper, Python 3.7+

## ✨ Features

- 🌡️ **Real-time temperature display** (hotend & bed)
- 📊 **Print progress tracking** with time estimates  
- 🎮 **Print status updates** (start/pause/resume/complete)
- 💨 **Fan speed monitoring**
- 📍 **Live position updates**
- 🔧 **Auto-detects TFT firmware** (MKS/BIGTREETECH)
- 🚀 **Native Moonraker integration**

## 🔌 Supported Hardware

- **BIGTREETECH TFT32** (recommended)
- **MKS TFT32 / TFT32_L v3**
- Other TFT32 displays with Marlin-compatible firmware

## 📋 Requirements

- Klipper + Moonraker setup
- TFT32 display connected via UART/serial
- Python 3.7+ with `pyserial`

## 🚀 Quick Installation

1. **Clone this repository:**
   ```bash
   cd ~
   git clone https://github.com/e-yaso/TFT32-KlipperInfo.git
   cd TFT32-KlipperInfo
   ```

2. **Run the installer:**
   ```bash
   ./install_plugin.sh
   ```

3. **Restart Moonraker:**
   ```bash
   sudo systemctl restart moonraker
   ```

4. **Check the logs:**
   ```bash
   tail -f ~/printer_data/logs/moonraker.log
   ```

## ⚙️ Configuration

The plugin is configured in your `moonraker.conf` file:

```ini
[tft32_plugin]
# Enable/disable the plugin
enabled: True

# Serial port - check with: ls /dev/tty* | grep -E "(ttyS|ttyAMA)"
serial_port: /dev/ttyS0

# Baud rate - must match your TFT firmware setting
baudrate: 115200

# Update interval in seconds
update_interval: 3.0
```

### 🔄 Auto-Update Configuration

For automatic updates when new versions are released, add this to your `moonraker.conf`:

```ini
[update_manager tft32_plugin]
type: git_repo
channel: dev
path: ~/TFT32-KlipperInfo
origin: https://github.com/e-yaso/TFT32-KlipperInfo.git
managed_services: moonraker
primary_branch: main
install_script: install_plugin.sh
refresh_interval: 24
enable_version_rollback: True
```

This enables:
- 🔄 **Automatic updates** when new versions are pushed
- 📱 **Mainsail/Fluidd integration** for manual updates
- 🔒 **Version rollback** if needed
- ⏰ **Daily update checks**

### Common Serial Configurations

| TFT Type | Port | Baud Rate |
|----------|------|-----------|
| BIGTREETECH TFT32 | `/dev/ttyS0` | 57600 |
| MKS TFT32 | `/dev/ttyS0` | 115200 |
| USB TFT | `/dev/ttyUSB0` | 115200 |

## 🔧 Hardware Connection

### Raspberry Pi GPIO (UART)

Connect your TFT to the Raspberry Pi's GPIO pins:

```
Pi GPIO 14 (TX) ──── TFT RX
Pi GPIO 15 (RX) ──── TFT TX  
Pi GND         ──── TFT GND
```

**Enable UART in `/boot/config.txt`:**
```
enable_uart=1
dtoverlay=disable-bt
```

## 📊 What You'll See

Once running, your TFT will display:

- **Temperature readings** updating every 3 seconds
- **Print progress** as percentage and time remaining  
- **Print status changes** (printing/paused/completed)
- **Layer information** (real data from PrusaSlicer or estimated)
- **Fan speed** as PWM values
- **Position updates** during moves

## 🔍 Troubleshooting

### Plugin Not Loading
```bash
# Check Moonraker logs
tail -f ~/printer_data/logs/moonraker.log | grep -i tft32

# Verify plugin file exists
ls -la ~/moonraker/moonraker/extras/tft32_plugin.py
```

### TFT Not Responding
```bash
# Check serial ports
ls /dev/tty* | grep -E "(ttyS|ttyAMA|ttyUSB)"

# Test serial connection
sudo chmod 666 /dev/ttyS0  # or your port
```

### Wrong Baud Rate
- Check your TFT firmware configuration
- Common rates: 57600, 115200, 250000
- BIGTREETECH usually uses 57600
- MKS typically uses 115200

## 📁 Project Files

- `tft32_plugin.py` - Main Moonraker plugin (v1.1.0)
- `tft32_final.py` - Standalone version (for testing)
- `config.py` - Configuration settings
- `install_plugin.sh` - Automated installer
- `moonraker_tft32.conf` - Configuration template
- `moonraker_update_config.conf` - Auto-update configuration  

## 📋 Version History

### v1.0.0 (2025-01-25) ✅ STABLE
- ✅ **Production ready** Moonraker plugin
- ✅ **Auto-detects** TFT firmware (MKS/BIGTREETECH)
- ✅ **Real-time data** from Klipper via klippy_apis
- ✅ **Print status integration** with M118 action codes
- ✅ **Display-only mode** for reliability
- ✅ **Reduced logging** for minimal log file size
- ✅ **Automated installer** with dependency management
- ✅ **Comprehensive documentation**
- 🧪 **Tested**: BIGTREETECH TFT32, Raspberry Pi, Moonraker

## 🎯 Display-Only Mode

This plugin operates in **display-only mode**, meaning:

- ✅ TFT shows real-time printer data
- ✅ Print status updates automatically
- ❌ TFT touch controls disabled (no two-way communication)
- ❌ Manual commands from TFT not processed

This ensures reliable operation while providing comprehensive printer monitoring.

## 🤝 Contributing

Found a bug or want to add a feature? Please open an issue or submit a pull request!

## 📄 License

This project is open source. Feel free to use, modify, and distribute.

---

**Need help?** Check the [Troubleshooting](#-troubleshooting) section or open an issue. 