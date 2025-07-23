# TFT32-KlipperInfo Project Summary

## What This Project Does

This project connects your **MKS TFT32 display** to a **Raspberry Pi running Klipper** via serial communication. It displays real-time printer information (temperatures, print status, progress) on your TFT32 **without requiring any firmware modifications**.

## How It Works

1. **Fetches data** from Klipper via Moonraker API
2. **Formats data** as standard G-code responses (M105, M27, etc.)
3. **Sends responses** to TFT32 via serial/UART
4. **TFT32 displays** the information using its existing interface

Your TFT32 thinks it's communicating with a printer mainboard, but it's actually getting Klipper data!

## Project Files

### Core Components
- **`moonraker_client.py`** - Connects to Moonraker API and fetches printer data
- **`tft32_serial_client.py`** - Handles serial communication with MKS TFT32
- **`klipper_tft32_monitor.py`** - Main application that ties everything together

### Configuration & Setup
- **`config.py`** - Configuration settings (Moonraker host, serial port, etc.)
- **`requirements.txt`** - Python dependencies (requests, websockets, pyserial)
- **`install.sh`** - Automated installation script for Raspberry Pi
- **`README.md`** - Complete setup instructions and troubleshooting

## Hardware Connection

```
MKS TFT32      →    Raspberry Pi
VCC (5V)       →    Pin 2 (5V)
GND            →    Pin 6 (GND)
TX             →    Pin 10 (GPIO15, RxD)
RX             →    Pin 8 (GPIO14, TxD)
```

## Installation Steps

1. **Wire TFT32** to Raspberry Pi UART pins
2. **Enable serial** in `raspi-config` 
3. **Run install script**: `./install.sh`
4. **Configure settings** in `config.py`
5. **Test**: `python3 klipper_tft32_monitor.py`
6. **Enable service**: `sudo systemctl start klipper-display.service`

## Key Features

- ✅ **No firmware flashing** required
- ✅ **Real-time temperature** monitoring
- ✅ **Print status** and progress display
- ✅ **Automatic reconnection** handling
- ✅ **System service** for auto-start
- ✅ **Comprehensive logging** and error handling

## Notes

- Works with existing MKS TFT32 firmware
- Tested with Klipper/Moonraker setup
- Serial communication at 115200 baud
- Handles standard G-code commands from TFT32
- Responds with appropriate printer status data 