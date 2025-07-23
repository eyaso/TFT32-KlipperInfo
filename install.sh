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

# Check if we can install globally or need virtual environment
if pip3 install --dry-run requests >/dev/null 2>&1; then
    echo "Installing packages globally..."
    pip3 install -r requirements.txt
else
    echo "System requires virtual environment or system packages..."
    
    # Try to install via apt first (preferred method)
    echo "Attempting to install via apt..."
    sudo apt install -y python3-requests python3-serial python3-websockets
    
    # Check if packages are available, if not use virtual environment
    if ! python3 -c "import requests, serial, websockets" >/dev/null 2>&1; then
        echo "Apt packages not sufficient, creating virtual environment..."
        
        # Install python3-venv if not available
        sudo apt install -y python3-venv python3-full
        
        # Create virtual environment
        python3 -m venv venv
        
        # Install packages in virtual environment
        ./venv/bin/pip install -r requirements.txt
        
        echo "Virtual environment created in ./venv/"
        echo "To activate: source venv/bin/activate"
        
        # Update the systemd service to use virtual environment
        VENV_PYTHON="$(pwd)/venv/bin/python3"
    else
        echo "Successfully installed via apt packages"
        VENV_PYTHON="/usr/bin/python3"
    fi
fi

# Determine which Python to use
if [ -z "$VENV_PYTHON" ]; then
    VENV_PYTHON="/usr/bin/python3"
fi

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
ExecStart=$VENV_PYTHON $(pwd)/klipper_tft32_monitor.py
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
echo "2. Test the installation:"
if [ -f "venv/bin/python3" ]; then
    echo "   source venv/bin/activate && python3 klipper_tft32_monitor.py"
    echo "   (or directly: ./venv/bin/python3 klipper_tft32_monitor.py)"
else
    echo "   python3 klipper_tft32_monitor.py"
fi
echo "3. If the test works, start the service: sudo systemctl start klipper-display.service"
echo "4. Check service status: sudo systemctl status klipper-display.service"
echo ""
echo "IMPORTANT: You may need to log out and log back in for group changes to take effect."
echo "If you encounter permission issues, reboot your Pi and try again."
echo ""
echo "For troubleshooting, check the README.md file." 