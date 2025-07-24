#!/bin/bash

# TFT32 Setup Verification Script
# Checks if everything is configured correctly

echo "🔍 TFT32 Setup Verification"
echo "=========================="

# Check files exist
echo "📁 Checking required files..."
required_files=(
    "klipper_tft32_monitor.py"
    "tft32_gcode_client.py"
    "tft32_connection_helper.py"
    "moonraker_client.py"
    "config.py"
    "requirements.txt"
    "start.sh"
)

missing_files=0
for file in "${required_files[@]}"; do
    if [ -f "$file" ]; then
        echo "  ✅ $file"
    else
        echo "  ❌ $file (MISSING)"
        missing_files=$((missing_files + 1))
    fi
done

if [ $missing_files -gt 0 ]; then
    echo "❌ Missing $missing_files required files. Please re-run install.sh"
    exit 1
fi

# Check Python
echo ""
echo "🐍 Checking Python environment..."
if python3 -c "import sys; print(f'Python {sys.version}')" 2>/dev/null; then
    echo "  ✅ Python 3 available"
else
    echo "  ❌ Python 3 not found"
    exit 1
fi

# Check Python packages
echo ""
echo "📦 Checking Python packages..."
packages=("serial" "requests" "websockets")

if [ -d "venv" ]; then
    echo "  📦 Using virtual environment"
    source venv/bin/activate
    python_cmd="python3"
else
    echo "  📦 Using system Python"
    python_cmd="python3"
fi

missing_packages=0
for package in "${packages[@]}"; do
    if $python_cmd -c "import $package" 2>/dev/null; then
        echo "  ✅ $package"
    else
        echo "  ❌ $package (MISSING)"
        missing_packages=$((missing_packages + 1))
    fi
done

if [ $missing_packages -gt 0 ]; then
    echo "❌ Missing $missing_packages Python packages. Please re-run install.sh"
    exit 1
fi

# Check serial ports
echo ""
echo "🔌 Checking serial ports..."
if ls /dev/ttyS* >/dev/null 2>&1; then
    echo "  ✅ Serial ports found:"
    ls -la /dev/ttyS* | while read line; do echo "     $line"; done
else
    echo "  ⚠️  No /dev/ttyS* ports found"
fi

if ls /dev/ttyAMA* >/dev/null 2>&1; then
    echo "  ✅ UART ports found:"
    ls -la /dev/ttyAMA* | while read line; do echo "     $line"; done
fi

# Check user groups
echo ""
echo "👤 Checking user permissions..."
if groups $USER | grep -q dialout; then
    echo "  ✅ User $USER is in dialout group"
else
    echo "  ❌ User $USER is NOT in dialout group"
    echo "     Run: sudo usermod -a -G dialout $USER"
    echo "     Then log out and log back in"
fi

# Check Moonraker
echo ""
echo "🌙 Checking Moonraker connection..."
if curl -s http://localhost:7125/server/info >/dev/null 2>&1; then
    echo "  ✅ Moonraker is accessible at localhost:7125"
else
    echo "  ⚠️  Cannot connect to Moonraker at localhost:7125"
    echo "     Make sure Klipper/Moonraker is running"
fi

# Check systemd service
echo ""
echo "⚙️  Checking systemd service..."
if systemctl list-unit-files | grep -q klipper-tft32.service; then
    echo "  ✅ klipper-tft32.service exists"
    
    if systemctl is-enabled klipper-tft32.service >/dev/null 2>&1; then
        echo "  ✅ Service is enabled for auto-start"
    else
        echo "  ⚠️  Service is not enabled for auto-start"
        echo "     Run: sudo systemctl enable klipper-tft32.service"
    fi
    
    if systemctl is-active klipper-tft32.service >/dev/null 2>&1; then
        echo "  ✅ Service is currently running"
    else
        echo "  ⚠️  Service is not running"
        echo "     Run: sudo systemctl start klipper-tft32.service"
    fi
else
    echo "  ❌ klipper-tft32.service not found"
    echo "     Please re-run install.sh"
fi

echo ""
echo "🎯 Setup Summary:"

# Overall status
errors=0
if [ $missing_files -gt 0 ]; then errors=$((errors + 1)); fi
if [ $missing_packages -gt 0 ]; then errors=$((errors + 1)); fi
if ! groups $USER | grep -q dialout; then errors=$((errors + 1)); fi

if [ $errors -eq 0 ]; then
    echo "✅ Setup looks good! Ready to run."
    echo ""
    echo "🚀 Next steps:"
    echo "   1. Test connection: ./start.sh --test-connection"
    echo "   2. Start monitor:   ./start.sh"
    echo "   3. Enable service:  sudo systemctl start klipper-tft32.service"
else
    echo "⚠️  Found $errors issues that need attention."
    echo ""
    echo "🔧 Recommended fixes:"
    if [ $missing_files -gt 0 ]; then
        echo "   - Re-run: ./install.sh"
    fi
    if [ $missing_packages -gt 0 ]; then
        echo "   - Re-run: ./install.sh"
    fi
    if ! groups $USER | grep -q dialout; then
        echo "   - Add to group: sudo usermod -a -G dialout $USER"
        echo "   - Then reboot or log out/in"
    fi
fi

echo ""
echo "📚 Documentation:"
echo "   - README.md for basic usage"
echo "   - TFT_CONNECTION_FIX.md for connection troubleshooting"
echo "   - README_STANDARD.md for technical details" 