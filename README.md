# Klipper MKS TFT32 Display Monitor

This project connects an MKS TFT32 display to your Raspberry Pi running Klipper/Moonraker via serial communication to show real-time printer information including temperatures, print status, and progress. **No firmware flashing required** - works with existing MKS TFT32 firmware!

## Features

- Real-time bed and hotend temperature display
- Print status and progress monitoring
- Connection status indicator
- Color-coded temperature warnings
- Progress bar for active prints
- Automatic reconnection handling
- Clean error messages

## Hardware Requirements

- Raspberry Pi 3/4 with Klipper and Moonraker installed
- MKS TFT32 display (any version with existing firmware)
- Connecting wires for serial (UART) communication

## How It Works

This solution uses **serial communication** to send printer data to your MKS TFT32. The Python application:
1. Fetches data from Klipper via Moonraker API
2. Formats the data as standard G-code responses (like M105 temperature reports)  
3. Sends these responses to your TFT32 via serial
4. Your TFT32 displays the information using its existing interface

**No firmware flashing needed!** Your TFT32 thinks it's talking to a printer mainboard.

## Wiring Diagram

Connect your MKS TFT32 to the Raspberry Pi as follows:

| MKS TFT32 Pin | Raspberry Pi Pin | GPIO | Description |
|---------------|------------------|------|-------------|
| VCC (5V)      | Pin 2            | 5V   | Power       |
| GND           | Pin 6            | GND  | Ground      |
| TX            | Pin 10           | GPIO15 (RX) | TFT transmit to Pi receive |
| RX            | Pin 8            | GPIO14 (TX) | TFT receive from Pi transmit |

**Note:** Some TFT32 versions may have different pin labels (like UART_TX/UART_RX). Use the UART/serial pins, not the ones for connecting to printer mainboard.

## Installation

### 1. Install System Dependencies

```bash
sudo apt update
sudo apt install python3-pip python3-dev
```

### 2. Enable Serial Interface

```bash
sudo raspi-config
```

- Navigate to "Interfacing Options" → "Serial Port"
- "Would you like a login shell to be accessible over serial?" → **No**
- "Would you like the serial port hardware to be enabled?" → **Yes**
- Reboot your Pi: `sudo reboot`

### 3. Install Python Dependencies

```bash
cd /home/pi  # or your preferred directory
git clone <this-repository>  # or download the files
cd TFT32-KlipperInfo

pip3 install -r requirements.txt
```

### 4. Configure Your Setup

Edit `config.py` to match your setup:

```python
# If running on a different machine than Klipper
MOONRAKER_HOST = "192.168.8.203"  # Your Pi's IP address

# Adjust display rotation if needed
DISPLAY_ROTATION = 90  # 0, 90, 180, or 270

# Modify GPIO pins if your wiring is different
DISPLAY_PINS = {
    'cs': 'CE0',     # Chip Select
    'dc': 'D25',     # Data/Command  
    'rst': None      # Reset pin (None if not connected)
}
```

### 5. Test the Installation

```bash
python3 klipper_tft32_monitor.py
```

If everything is working correctly, you should see:
- Console output showing Moonraker and TFT32 connection status
- Your TFT32 displaying current printer data (temperatures, status, etc.)

Press `Ctrl+C` to stop the test.

## Auto-Start on Boot

To automatically start the monitor when your Pi boots:

### 1. Create a systemd service

```bash
sudo nano /etc/systemd/system/klipper-display.service
```

Add the following content:

```ini
[Unit]
Description=Klipper TFT32 Display Monitor
After=network.target moonraker.service
Wants=moonraker.service

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/TFT32-KlipperInfo
ExecStart=/usr/bin/python3 klipper_tft32_monitor.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### 2. Enable and start the service

```bash
sudo systemctl enable klipper-display.service
sudo systemctl start klipper-display.service
```

### 3. Check service status

```bash
sudo systemctl status klipper-display.service
```

## Troubleshooting

### Display Not Working

1. **Check wiring connections** - Ensure all pins are connected correctly
2. **Verify SPI is enabled** - Run `lsmod | grep spi` to confirm SPI modules are loaded
3. **Check permissions** - Make sure your user is in the `spi` group: `sudo usermod -a -G spi pi`
4. **Test SPI communication** - Install `spi-tools`: `sudo apt install spi-tools` and test with `spi-config`

### Moonraker Connection Issues

1. **Check Moonraker is running** - `sudo systemctl status moonraker`
2. **Verify the correct IP/port** - Test with `curl http://localhost:7125/server/info`
3. **Check firewall settings** - Ensure port 7125 is accessible
4. **Review Moonraker logs** - `journalctl -u moonraker -f`

### Common Error Messages

- **"Cannot connect to Moonraker"** - Check network connection and Moonraker status
- **"Failed to initialize display"** - Verify wiring and SPI configuration
- **"Permission denied"** - Add user to appropriate groups: `sudo usermod -a -G spi,gpio pi`

### Display is Rotated Wrong

Edit `config.py` and change `DISPLAY_ROTATION`:
- `0` - Normal orientation
- `90` - Rotated 90° clockwise
- `180` - Upside down
- `270` - Rotated 90° counter-clockwise

### Logs and Debugging

- View real-time logs: `tail -f klipper_tft32.log`
- Enable debug logging: Set `LOG_LEVEL = "DEBUG"` in `config.py`
- Service logs: `journalctl -u klipper-display.service -f`

## Customization

### Adding New Information

You can extend the functionality by modifying the code:

1. Add new G-code response handlers in `tft32_serial_client.py`
2. Update the main monitoring loop in `klipper_tft32_monitor.py`
3. Add corresponding API calls in `moonraker_client.py`

### Changing Response Format

Edit the response methods in `TFT32SerialClient` to customize what data is sent to your TFT32.

### Different TFT Models

For other MKS TFT displays:
1. Update serial port and baudrate in `config.py`
2. Adjust command handling if your TFT uses different G-code commands
3. Test and modify response formats as needed

## Contributing

Feel free to submit issues, feature requests, or pull requests to improve this project.

## License

This project is open source. Use and modify as needed for your 3D printing setup. 