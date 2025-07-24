#!/usr/bin/env python3
"""
Raw Serial Test - Check if ANY data is coming from TFT
"""

import serial
import time
import config

def test_raw_serial():
    print("🔍 Raw Serial Port Test")
    print("🎯 Testing if ANY data comes from TFT...")
    print("=" * 50)
    
    port = config.TFT32_SERIAL_PORT  
    baudrate = config.TFT32_BAUDRATE
    
    try:
        ser = serial.Serial(port, baudrate, timeout=0.1)
        print(f"✅ Opened {port} at {baudrate} baud")
        print("📡 Listening for ANY incoming data...")
        print("🎮 Go to TFT Terminal and send M105 manually")
        print("⏰ Listening for 30 seconds...")
        print()
        
        start_time = time.time()
        byte_count = 0
        
        while time.time() - start_time < 30:
            if ser.in_waiting > 0:
                # Read raw bytes
                raw_data = ser.read(ser.in_waiting)
                byte_count += len(raw_data)
                
                print(f"📥 RAW BYTES ({len(raw_data)}): {raw_data}")
                print(f"📝 AS TEXT: '{raw_data.decode('utf-8', errors='replace').strip()}'")
                print(f"🔢 HEX: {raw_data.hex()}")
                print("-" * 40)
            
            time.sleep(0.1)
        
        print(f"\n📊 Total bytes received: {byte_count}")
        if byte_count == 0:
            print("❌ NO DATA RECEIVED - Serial connection problem!")
            print("🔧 Possible issues:")
            print("   - Wrong serial port (/dev/ttyS0 vs /dev/ttyAMA0)")
            print("   - Wrong baud rate")
            print("   - Wiring issue (TX/RX swapped)")
            print("   - TFT not actually sending")
            print("   - Serial port permissions")
        else:
            print("✅ Data received - Serial connection working!")
            
    except Exception as e:
        print(f"❌ Serial error: {e}")
    finally:
        if 'ser' in locals():
            ser.close()

if __name__ == "__main__":
    test_raw_serial() 