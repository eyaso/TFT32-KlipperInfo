# 🖥️ **Klipper TFT32 Display Monitor**

Connect your **MKS TFT32** display to a **Raspberry Pi** running **Klipper/Moonraker** to display real-time printer information.

**✅ What this does:**
- Shows **real-time temperatures** (hotend, bed)
- Displays **print status** and progress
- Works with **existing TFT firmware** (no flashing required)
- **Fixes "no printer attached"** connection issue
- Uses **standard G-code protocol** for maximum compatibility

---

## 🚀 **Super Simple Setup**

### **1. Install Everything**
```bash
git clone https://github.com/your-repo/TFT32-KlipperInfo.git
cd TFT32-KlipperInfo
chmod +x install.sh
./install.sh
```

### **2. Start the Monitor**
```bash
chmod +x start.sh
./start.sh
```

**That's it!** Your TFT should now show "Connected" instead of "no printer attached" and display real-time data.

---

## 🔌 **Wiring**

Connect TFT32 to Raspberry Pi:

| **TFT32 Pin** | **Raspberry Pi Pin** | **Description** |
|---------------|---------------------|-----------------|
| **VCC**       | 5V (Pin 2 or 4)    | Power          |
| **GND**       | GND (Pin 6)         | Ground         |
| **TX**        | GPIO 15 (Pin 10)    | TFT → Pi       |
| **RX**        | GPIO 14 (Pin 8)     | Pi → TFT       |

---

## 📋 **Usage**

### **Start Options:**
```bash
# Simple start
./start.sh

# Test connection first
./start.sh --test-connection

# Only test connection
./start.sh --connection-only

# Get help
./start.sh --help
```

### **Service Management:**
```bash
# Auto-start on boot
sudo systemctl start klipper-tft32.service

# Check status
sudo systemctl status klipper-tft32.service

# View logs
journalctl -u klipper-tft32.service -f

# Stop service
sudo systemctl stop klipper-tft32.service
```

---

## 🔧 **Configuration**

Edit `config.py` to adjust settings:

```python
# Moonraker connection
MOONRAKER_HOST = "localhost"
MOONRAKER_PORT = 7125

# TFT32 serial connection
TFT32_SERIAL_PORT = "/dev/ttyS0"
TFT32_BAUDRATE = 115200

# Logging
LOG_LEVEL = "INFO"
LOG_FILE = "klipper_tft32.log"
```

---

## 🛠️ **Troubleshooting**

### **"No printer attached" on TFT:**
```bash
# Run connection helper
python3 tft32_connection_helper.py
```

### **Serial port issues:**
```bash
# Enable serial hardware
sudo raspi-config
# → Interface Options → Serial Port
# → No to login shell, Yes to hardware

# Check serial ports
ls -la /dev/ttyS* /dev/ttyAMA*

# Test loopback (connect TX to RX)
echo "test" > /dev/ttyS0
cat /dev/ttyS0
```

### **Permission errors:**
```bash
# Add user to dialout group
sudo usermod -a -G dialout $USER

# Reboot to apply changes
sudo reboot
```

### **Moonraker connection:**
```bash
# Test Moonraker API
curl http://localhost:7125/server/info

# Add to moonraker.conf if needed:
[authorization]
trusted_clients:
    127.0.0.1
    localhost
```

---

## 📚 **Advanced Documentation**

- **`TFT_CONNECTION_FIX.md`** - Details about the connection detection fix
- **`README_STANDARD.md`** - Complete technical documentation  
- **`STANDARD_GCODE_MIGRATION.md`** - G-code protocol information

---

## ✨ **Features**

### **Current Features:**
- ✅ **Real-time temperature display**
- ✅ **Print status monitoring** 
- ✅ **Connection status** (no more "no printer attached")
- ✅ **Standard G-code compatibility**
- ✅ **Auto-start service**
- ✅ **Easy installation**

### **Future Features:**
- 🔄 **Printer control** (heat, move, etc.)
- 🔄 **File management** 
- 🔄 **Print job control**
- 🔄 **Custom TFT firmware** (optional)

---

## 🎯 **What's Special**

This solution is **unique** because:

1. **No TFT firmware flashing required** - Works with existing firmware
2. **Fixes connection detection** - Uses proper `@:` prefix format
3. **Standard G-code protocol** - Maximum compatibility
4. **Simple installation** - One script installs everything
5. **Production ready** - Includes systemd service, logging, error handling

---

## 🆘 **Support**

**Quick Help:**
```bash
./start.sh --help                    # Startup options
python3 tft32_connection_helper.py   # Fix connection issues
journalctl -u klipper-tft32.service  # Check logs
```

**Common Issues:**
- **"No printer attached"** → Run `tft32_connection_helper.py`
- **Permission denied** → Reboot after running `install.sh`
- **Can't connect to Moonraker** → Check Klipper/Moonraker is running
- **Serial port not found** → Enable serial in `raspi-config`

---

## 🏆 **Success!**

When working correctly, you should see:
- **TFT Status:** "Connected" (not "no printer attached")
- **Temperature Display:** Real-time hotend/bed temperatures
- **Print Information:** Status, progress, time remaining
- **Responsive Interface:** Touch controls work normally

📚 **Need Help?** See `TROUBLESHOOTING.md` for common issues and solutions.

**🎉 Enjoy your connected TFT32 display!** 