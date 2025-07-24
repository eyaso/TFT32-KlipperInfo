#!/usr/bin/env python3
"""
Show detailed TFT32 communication for debugging
This script temporarily modifies the log level to show all TFT communication
"""

import logging
import sys
import os

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import config
from klipper_tft32_monitor import KlipperTFT32StandardMonitor

def main():
    print("🔍 TFT32 Communication Monitor")
    print("=" * 50)
    print("This will show ALL messages sent to/from the TFT")
    print("📥 TFT >> PI: Messages FROM TFT TO Raspberry Pi")
    print("📤 PI >> TFT: Messages FROM Raspberry Pi TO TFT")
    print("🔄 Status updates every 30 seconds")
    print("Press Ctrl+C to stop")
    print("=" * 50)
    
    # Temporarily set logging to INFO level to see communication
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler()
        ]
    )
    
    # Create and run monitor
    monitor = KlipperTFT32StandardMonitor()
    try:
        monitor.run()
    except KeyboardInterrupt:
        print("\n🛑 Stopping communication monitor...")
        monitor.shutdown()

if __name__ == "__main__":
    main() 