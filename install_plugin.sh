#!/bin/bash
# TFT32 Moonraker Plugin Installer
# Installs the TFT32 plugin for Moonraker

set -e

echo "🚀 TFT32 Moonraker Plugin Installer"
echo "==================================="

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo "❌ Please do not run this script as root"
    exit 1
fi

# Check if Moonraker is installed
MOONRAKER_DIR=""
if [ -d "$HOME/moonraker" ]; then
    MOONRAKER_DIR="$HOME/moonraker"
elif [ -d "/home/pi/moonraker" ]; then
    MOONRAKER_DIR="/home/pi/moonraker"
else
    echo "❌ Moonraker directory not found"
    echo "💡 Expected: ~/moonraker or /home/pi/moonraker"
    exit 1
fi

echo "✅ Found Moonraker at: $MOONRAKER_DIR"

# Create extras directory if it doesn't exist
COMPONENTS_DIR="$MOONRAKER_DIR/moonraker/components"
mkdir -p "$COMPONENTS_DIR"

# Copy plugin file
PLUGIN_SOURCE="./tft32_plugin.py"
PLUGIN_DEST="$COMPONENTS_DIR/tft32_plugin.py"

if [ ! -f "$PLUGIN_SOURCE" ]; then
    echo "❌ Plugin file not found: $PLUGIN_SOURCE"
    echo "💡 Make sure you're running this from the TFT32-KlipperInfo directory"
    exit 1
fi

echo "📦 Installing plugin..."
cp "$PLUGIN_SOURCE" "$PLUGIN_DEST"
chmod +x "$PLUGIN_DEST"

echo "✅ Plugin installed to: $PLUGIN_DEST"

# Install Python dependencies
echo "📚 Installing Python dependencies..."

# Try different methods to install pyserial
if command -v apt &> /dev/null; then
    echo "🔧 Using apt to install python3-serial..."
    sudo apt update
    sudo apt install -y python3-serial
elif pip3 install --break-system-packages pyserial 2>/dev/null; then
    echo "✅ Installed pyserial with --break-system-packages"
elif python3 -m pip install --user pyserial 2>/dev/null; then
    echo "✅ Installed pyserial with --user flag"
else
    echo "⚠️ Could not install pyserial automatically"
    echo "💡 Please install manually with:"
    echo "   sudo apt install python3-serial"
    echo "   OR: pip3 install --user pyserial"
fi

# Check moonraker.conf location
CONF_LOCATIONS=(
    "$HOME/printer_data/config/moonraker.conf"
    "$HOME/klipper_config/moonraker.conf" 
    "/home/pi/printer_data/config/moonraker.conf"
    "/home/pi/klipper_config/moonraker.conf"
)

CONF_FILE=""
for location in "${CONF_LOCATIONS[@]}"; do
    if [ -f "$location" ]; then
        CONF_FILE="$location"
        break
    fi
done

if [ -z "$CONF_FILE" ]; then
    echo "⚠️ moonraker.conf not found automatically"
    echo "💡 Please manually add the configuration section to your moonraker.conf:"
    echo ""
    cat moonraker_tft32.conf
    echo ""
else
    echo "✅ Found moonraker.conf at: $CONF_FILE"
    
    # Check if plugin section already exists
    if grep -q "\[tft32_plugin\]" "$CONF_FILE"; then
        echo "⚠️ Plugin section already exists in moonraker.conf"
        echo "💡 Please review and update the configuration manually if needed"
    else
        echo "📝 Adding plugin configuration to moonraker.conf..."
        echo "" >> "$CONF_FILE"
        echo "# TFT32 Plugin Configuration" >> "$CONF_FILE"
        cat moonraker_tft32.conf >> "$CONF_FILE"
        echo "✅ Configuration added to moonraker.conf"
    fi
fi

echo ""
echo "🎉 Installation complete!"
echo ""
echo "📋 Next steps:"
echo "1. Review the configuration in moonraker.conf:"
echo "   - Check serial_port (usually /dev/ttyS0 or /dev/ttyAMA0)"
echo "   - Verify baudrate matches your TFT firmware"
echo ""
echo "2. Restart Moonraker:"
echo "   sudo systemctl restart moonraker"
echo ""
echo "3. Check the logs:"
echo "   tail -f ~/printer_data/logs/moonraker.log"
echo ""
echo "4. Verify the plugin is loaded:"
echo "   Look for 'TFT32 Plugin starting...' in the logs"
echo ""
echo "⚠️ Make sure your TFT is connected to the correct serial port!"
echo "🔧 You can test serial ports with: ls /dev/tty* | grep -E '(ttyS|ttyAMA|ttyUSB)'" 