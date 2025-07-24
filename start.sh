#!/bin/bash

# Simple startup script for Klipper TFT32 Monitor
# This script makes it easy to run the monitor

echo "🚀 Starting Klipper TFT32 Monitor..."

# Check if virtual environment exists
if [ -d "venv" ]; then
    echo "📦 Using virtual environment..."
    source venv/bin/activate
    PYTHON_CMD="python3"
else
    echo "📦 Using system Python..."
    PYTHON_CMD="python3"
fi

# Check if connection helper should be run first
if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    echo ""
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  --test-connection    Test TFT connection first"
    echo "  --connection-only    Only run connection helper"
    echo "  --help, -h          Show this help"
    echo ""
    echo "Examples:"
    echo "  $0                   Start the monitor directly"
    echo "  $0 --test-connection Test connection, then start monitor"
    echo "  $0 --connection-only Only establish connection"
    echo ""
    exit 0
fi

# Handle connection testing
if [ "$1" = "--test-connection" ]; then
    echo "🔗 Testing TFT connection first..."
    $PYTHON_CMD tft32_connection_helper.py --timeout 10
    
    if [ $? -eq 0 ]; then
        echo "✅ Connection test successful! Starting monitor..."
        sleep 2
    else
        echo "❌ Connection test failed. Please check wiring and try again."
        exit 1
    fi
elif [ "$1" = "--connection-only" ]; then
    echo "🔗 Running connection helper only..."
    $PYTHON_CMD tft32_connection_helper.py
    exit 0
fi

# Check if files exist
if [ ! -f "klipper_tft32_monitor.py" ]; then
    echo "❌ Monitor script not found. Please run install.sh first."
    exit 1
fi

# Check if Moonraker is accessible
echo "🌙 Checking Moonraker connection..."
if ! curl -s http://localhost:7125/server/info >/dev/null 2>&1; then
    echo "⚠️  Warning: Cannot connect to Moonraker at localhost:7125"
    echo "   Make sure Klipper/Moonraker is running and accessible"
    echo "   Edit config.py if using different IP/port"
    echo ""
fi

# Start the monitor
echo "📺 Starting TFT monitor..."
echo "   Press Ctrl+C to stop"
echo "   Check your TFT screen - should show 'Connected' status"
echo ""

$PYTHON_CMD klipper_tft32_monitor.py 