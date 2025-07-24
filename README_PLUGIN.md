# Moonraker TFT32 Plugin

A production-ready Moonraker plugin for BIGTREETECH TFT32 displays that enables seamless integration with Klipper/Moonraker.

## Features

- ✅ **OctoPrint Protocol Compatible** - Uses the same protocol as OctoPrint BTT Touch Support
- 🔄 **Real-time Updates** - Live temperature, progress, and status updates
- 🎮 **TFT Controls** - Pause, resume, cancel from TFT display
- 🔌 **Auto-reconnection** - Handles serial disconnections gracefully
- ⚙️ **Configurable** - Easy configuration via moonraker.conf
- 📊 **Progress Notifications** - Time remaining and completion percentage
- 🚀 **Async/Await** - Modern Python async architecture

## Quick Start

### 1. Test Serial Connection First

Before using the plugin, make sure your serial connection works:

```bash
# Test all available ports
./test_all_serial_ports.sh

# Test different baud rates
python3 test_baud_rates.py
```

### 2. Update Configuration

Update your `config.py` with the working serial port:

```python
TFT32_SERIAL_PORT = '/dev/ttyS0'  # or /dev/ttyAMA0
TFT32_BAUDRATE = 250000           # or 115200, etc.
```

### 3. Run Standalone

Test the plugin in standalone mode:

```bash
python3 start_tft_plugin.py
```

### 4. Install as Moonraker Plugin

Copy the plugin to Moonraker's extras directory:

```bash
cp moonraker_tft_plugin.py ~/moonraker/moonraker/components/
```

Add configuration to `moonraker.conf`:

```ini
[tft32_display]
serial_port: /dev/ttyS0
baudrate: 250000
update_interval: 2.0
```

Restart Moonraker:

```bash
sudo systemctl restart moonraker
```

## Configuration Options

| Option | Default | Description |
|--------|---------|-------------|
| `serial_port` | `/dev/ttyS0` | Serial port for TFT32 |
| `baudrate` | `250000` | Serial communication speed |
| `moonraker_host` | `localhost` | Moonraker host address |
| `moonraker_port` | `7125` | Moonraker port number |
| `update_interval` | `2.0` | Update frequency (seconds) |
| `serial_port_nr` | `0` | TFT serial port number |

## Protocol Details

The plugin uses standard Marlin G-code protocol with OctoPrint extensions:

### Commands Handled
- `M105` - Temperature requests
- `M115` - Firmware identification  
- `M114` - Position requests
- `M92` - Steps per mm
- Action commands (pause, resume, cancel)

### Responses Sent
- Temperature: `ok T:25.0 /0.0 B:22.0 /0.0 @:0 B@:0`
- Firmware: `FIRMWARE_NAME:Klipper HOST_ACTION_COMMANDS:1 EXTRUDER_COUNT:1`
- Capabilities: `Cap:EEPROM:1`, `Cap:AUTOREPORT_TEMP:1`, etc.
- Notifications: `M118 P0 A1 action:notification Time Left 01h23m45s`

## Troubleshooting

### TFT Shows "No Printer Attached"
1. Check serial port and baud rate
2. Verify wiring (TX/RX connections)
3. Test with raw serial tools first
4. Check TFT firmware configuration

### No Communication
1. Kill any existing monitor processes
2. Test different serial ports (`/dev/ttyAMA0`)
3. Try different baud rates (115200, 57600)
4. Check TFT Terminal for outgoing commands

### Plugin Errors
1. Check log file: `tft32_plugin.log`
2. Verify Moonraker is accessible
3. Check serial port permissions
4. Test in standalone mode first

## Architecture

```
┌─────────────────┐    HTTP     ┌─────────────────┐
│   Moonraker     │◄────────────┤  TFT32 Plugin   │
│   (Klipper)     │             │                 │
└─────────────────┘             └─────────────────┘
                                         │ Serial
                                         │ (UART)
                                         ▼
                                ┌─────────────────┐
                                │   TFT32 Display │
                                │   (BTT Firmware)│
                                └─────────────────┘
```

## Files Overview

- `moonraker_tft_plugin.py` - Main plugin (production ready)
- `start_tft_plugin.py` - Standalone test runner
- `moonraker_tft_config.conf` - Configuration example
- `config.py` - Local configuration file
- `test_all_serial_ports.sh` - Serial port testing
- `test_baud_rates.py` - Baud rate testing

## Development

### Standalone Mode
```bash
python3 start_tft_plugin.py
```

### Debug Mode
Enable debug logging in configuration:
```ini
[tft32_display]
log_level: DEBUG
```

### Testing
The plugin includes comprehensive error handling and auto-reconnection. Test by:
1. Disconnecting/reconnecting TFT
2. Restarting Moonraker
3. Sending commands from TFT Terminal

## License

MIT License - Feel free to modify and distribute. 