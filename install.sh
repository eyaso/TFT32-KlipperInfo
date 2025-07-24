#!/bin/bash

# Klipper TFT32 Display Monitor Installation Script  
# Standard G-code Version with Connection Detection Fix
# This script automates the installation process

set -e

echo "================================================="
echo "Klipper TFT32 Display Monitor Installer v2.0"
echo "Standard G-code Version with Connection Fix"
echo "================================================="

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo "❌ Please run this script as a regular user (not root)"
    exit 1
fi

echo "📦 Installing system dependencies..."
# Update system packages
sudo apt update

# Install required system packages
sudo apt install -y python3-pip python3-dev python3-venv python3-serial

# Check if serial is enabled
echo "🔌 Checking serial configuration..."
if ! ls /dev/ttyS* >/dev/null 2>&1 && ! ls /dev/ttyAMA* >/dev/null 2>&1; then
    echo "⚠️  Serial port not found. Please run 'sudo raspi-config' and enable serial hardware."
    echo "   Navigate to: Interfacing Options -> Serial Port"
    echo "   Answer No to login shell, Yes to serial port hardware"
    echo "   Then reboot and run this script again."
    exit 1
fi

echo "🐍 Installing Python dependencies..."

# Try installing packages directly first
if python3 -c "import sys; exit(0 if sys.version_info >= (3,7) else 1)" 2>/dev/null; then
    # Try system packages first
    if sudo apt install -y python3-requests python3-websockets 2>/dev/null; then
        echo "✅ Successfully installed via system packages"
        PYTHON_CMD="python3"
    else
        echo "📦 Creating virtual environment for Python packages..."
        
        # Create virtual environment
        python3 -m venv venv
        source venv/bin/activate
        
        # Install packages in virtual environment
        pip install -r requirements.txt
        
        echo "✅ Virtual environment created in ./venv/"
        PYTHON_CMD="$(pwd)/venv/bin/python3"
    fi
else
    echo "❌ Python 3.7+ required but not found"
    exit 1
fi

# Add user to dialout group for serial access
echo "🔧 Configuring serial port access..."
sudo usermod -a -G dialout $USER

# Make scripts executable
chmod +x klipper_tft32_monitor.py 2>/dev/null || true
chmod +x tft32_connection_helper.py 2>/dev/null || true

# Create systemd service for auto-start
echo "⚙️  Creating systemd service..."
sudo tee /etc/systemd/system/klipper-tft32.service > /dev/null <<EOF
[Unit]
Description=Klipper TFT32 Display Monitor (Standard G-code)
After=network.target moonraker.service
Wants=moonraker.service

[Service]
Type=simple
User=$USER
Group=dialout
WorkingDirectory=$(pwd)
ExecStart=$PYTHON_CMD $(pwd)/klipper_tft32_monitor.py
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# Enable systemd service (but don't start yet)
echo "🔄 Enabling service for auto-start..."
sudo systemctl daemon-reload
sudo systemctl enable klipper-tft32.service

echo ""
echo "================================================="
echo "✅ Installation completed successfully!"
echo "================================================="
echo ""
echo "🎯 What was installed:"
echo "   - Python dependencies for Klipper/Moonraker communication"
echo "   - TFT32 connection helper with @: prefix fix"
echo "   - Standard G-code communication protocol"
echo "   - Systemd service for auto-start"
echo ""
echo "🚀 Quick Start:"
echo "   1. Test connection: python3 tft32_connection_helper.py"
echo "   2. Start monitor:   python3 klipper_tft32_monitor.py"
echo "   3. Enable auto-start: sudo systemctl start klipper-tft32.service"
echo ""
echo "📋 Service Management:"
echo "   - Start:   sudo systemctl start klipper-tft32.service"
echo "   - Stop:    sudo systemctl stop klipper-tft32.service"
echo "   - Status:  sudo systemctl status klipper-tft32.service"
echo "   - Logs:    journalctl -u klipper-tft32.service -f"
echo ""
echo "🔧 Configuration:"
echo "   - Edit config.py to adjust settings (IP, ports, etc.)"
echo "   - TFT connection should show 'Connected' instead of 'no printer attached'"
echo ""
echo "⚠️  IMPORTANT: Log out and log back in (or reboot) for group changes to take effect"
echo "   If you get permission errors, reboot your Pi and try again."
echo ""
echo "📚 Documentation: See README_STANDARD.md for detailed setup guide"
echo "🆘 Troubleshooting: See TFT_CONNECTION_FIX.md for connection issues" 