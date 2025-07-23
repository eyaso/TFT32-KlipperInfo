#!/bin/bash

# Klipper TFT32 Display Monitor Installation Script
# This script automates the installation process

set -e

echo "========================================"
echo "Klipper TFT32 Display Monitor Installer"
echo "========================================"

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo "Please run this script as a regular user (not root)"
    exit 1
fi

# Update system packages
echo "Updating system packages..."
sudo apt update

# Install system dependencies
echo "Installing system dependencies..."
sudo apt install -y python3-pip python3-dev

# Check if serial is enabled
echo "Checking serial configuration..."
if ! ls /dev/ttyS* >/dev/null 2>&1; then
    echo "Serial port not found. Please run 'sudo raspi-config' and enable serial hardware."
    echo "Navigate to: Interfacing Options -> Serial Port"
    echo "Answer No to login shell, Yes to serial port hardware"
    echo "Then reboot and run this script again."
    exit 1
fi

# Install Python dependencies
echo "Installing Python dependencies..."
pip3 install -r requirements.txt

# Add user to dialout group for serial access
echo "Adding user to dialout group for serial access..."
sudo usermod -a -G dialout $USER

# Make the main script executable
chmod +x klipper_tft32_monitor.py

# Create systemd service
echo "Creating systemd service..."
sudo tee /etc/systemd/system/klipper-display.service > /dev/null <<EOF
[Unit]
Description=Klipper TFT32 Display Monitor
After=network.target moonraker.service
Wants=moonraker.service

[Service]
Type=simple
User=$USER
WorkingDirectory=$(pwd)
ExecStart=/usr/bin/python3 $(pwd)/klipper_tft32_monitor.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# Enable systemd service
echo "Enabling service for auto-start..."
sudo systemctl enable klipper-display.service

echo ""
echo "========================================"
echo "Installation completed successfully!"
echo "========================================"
echo ""
echo "Next steps:"
echo "1. Edit config.py to match your setup (IP address, pin configuration, etc.)"
echo "2. Test the installation: python3 klipper_tft32_monitor.py"
echo "3. If the test works, start the service: sudo systemctl start klipper-display.service"
echo "4. Check service status: sudo systemctl status klipper-display.service"
echo ""
echo "IMPORTANT: You may need to log out and log back in for group changes to take effect."
echo "If you encounter permission issues, reboot your Pi and try again."
echo ""
echo "For troubleshooting, check the README.md file." 