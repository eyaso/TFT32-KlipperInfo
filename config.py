"""
Configuration settings for Klipper TFT32 Display Monitor
"""

# Moonraker connection settings
MOONRAKER_HOST = "localhost"  # Change to your Raspberry Pi IP if running remotely
MOONRAKER_PORT = 7125

# TFT32 Serial settings
TFT32_SERIAL_PORT = "/dev/ttyS0"  # Serial port (GPIO14 TxD, GPIO15 RxD)
TFT32_BAUDRATE = 250000           # Common baudrate for MKS TFT displays

# Alternative serial ports:
# "/dev/ttyAMA0" - Primary UART (disable Bluetooth first)
# "/dev/ttyUSB0" - If using USB-to-serial adapter

# Update intervals (in seconds)
UPDATE_INTERVAL = 2.0  # How often to refresh display
CONNECTION_CHECK_INTERVAL = 10.0  # How often to check connection

# Logging configuration
LOG_LEVEL = "INFO"  # DEBUG, INFO, WARNING, ERROR
LOG_FILE = "klipper_tft32.log"

# Features to enable
SHOW_TEMPERATURES = True
SHOW_PRINT_STATUS = True 