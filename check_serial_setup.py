#!/usr/bin/env python3
"""
Serial Port Setup Checker
"""

import subprocess
import os
import config

def check_serial_setup():
    print("🔍 Serial Port Setup Checker")
    print("=" * 40)
    
    # Check configured port
    port = config.TFT32_SERIAL_PORT
    baud = config.TFT32_BAUDRATE
    print(f"📡 Configured: {port} at {baud} baud")
    print()
    
    # Check if port exists
    print("1️⃣ Checking if serial port exists...")
    if os.path.exists(port):
        print(f"✅ {port} exists")
    else:
        print(f"❌ {port} does NOT exist!")
        print("🔧 Try: ls /dev/tty*")
        return
    
    # Check permissions
    print("\n2️⃣ Checking permissions...")
    try:
        stat = os.stat(port)
        print(f"📋 Port permissions: {oct(stat.st_mode)[-3:]}")
        
        # Check if we can read
        with open(port, 'rb') as f:
            print("✅ Can open port for reading")
    except PermissionError:
        print("❌ Permission denied!")
        print(f"🔧 Try: sudo chmod 666 {port}")
        print(f"🔧 Or: sudo usermod -a -G dialout $USER")
        return
    except Exception as e:
        print(f"❌ Error: {e}")
        return
    
    # Check what processes are using the port
    print("\n3️⃣ Checking port usage...")
    try:
        result = subprocess.run(['fuser', port], capture_output=True, text=True)
        if result.stdout.strip():
            print(f"⚠️ Port in use by PIDs: {result.stdout.strip()}")
            print("🔧 Kill processes or restart Pi")
        else:
            print("✅ Port is free")
    except:
        print("❓ Could not check port usage")
    
    # Check available serial ports
    print("\n4️⃣ Available serial ports:")
    try:
        result = subprocess.run(['ls', '/dev/tty*'], capture_output=True, text=True)
        ports = [p for p in result.stdout.split() if 'ttyS' in p or 'ttyAMA' in p or 'ttyUSB' in p]
        for p in ports:
            print(f"📡 {p}")
        
        if '/dev/ttyAMA0' in ports and port != '/dev/ttyAMA0':
            print("\n💡 NOTE: /dev/ttyAMA0 is also available")
            print("   Try changing config.py: TFT32_SERIAL_PORT = '/dev/ttyAMA0'")
            
    except Exception as e:
        print(f"❌ Error listing ports: {e}")
    
    # Check raspi-config serial settings
    print("\n5️⃣ Raspberry Pi serial config:")
    try:
        # Check if serial console is disabled
        with open('/boot/cmdline.txt', 'r') as f:
            cmdline = f.read()
            if 'console=serial0' in cmdline:
                print("⚠️ Serial console is ENABLED - may interfere")
                print("🔧 Run: sudo raspi-config → Advanced → Serial")
                print("   Set: Shell over serial = NO, Hardware = YES")
            else:
                print("✅ Serial console appears disabled")
    except:
        print("❓ Could not check serial config")

if __name__ == "__main__":
    check_serial_setup() 