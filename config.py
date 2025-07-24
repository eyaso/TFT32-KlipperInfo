"""
Configuration settings for Klipper TFT32 Display Monitor
"""

# Moonraker connection settings
MOONRAKER_HOST = "localhost"  # Change to your Raspberry Pi IP if running remotely
MOONRAKER_PORT = 7125

# TFT32 Serial settings
TFT32_SERIAL_PORT = "/dev/ttyS0"  # Serial port (GPIO14 TxD, GPIO15 RxD)
TFT32_BAUDRATE = 115200           # BIGTREETECH firmware uses 115200 by default
# TFT32_BAUDRATE = 250000         # Try this if 115200 doesn't work
# TFT32_BAUDRATE = 9600           # Some older firmware uses 9600
# TFT32_BAUDRATE = 38400          # Alternative baud rate

# Alternative serial ports:
# "/dev/ttyAMA0" - Primary UART (disable Bluetooth first)
# "/dev/ttyUSB0" - If using USB-to-serial adapter

# 💡 TIP: If TFT doesn't respond, try different baud rates:
#    - Most BIGTREETECH firmware: 115200
#    - Some Marlin configurations: 250000  
#    - Older TFT firmware: 9600 or 38400
#    Change TFT32_BAUDRATE above and restart the monitor

# Update intervals (in seconds)
UPDATE_INTERVAL = 2.0  # How often to refresh display
CONNECTION_CHECK_INTERVAL = 10.0  # How often to check connection

# Logging configuration
LOG_LEVEL = "INFO"  # DEBUG, INFO, WARNING, ERROR
LOG_FILE = "klipper_tft32.log"

# Features to enable
SHOW_TEMPERATURES = True
SHOW_PRINT_STATUS = True 