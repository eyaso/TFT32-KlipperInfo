#!/usr/bin/env python3
"""
Test different baud rates on the configured serial port
"""

import serial
import time
import config

def test_baud_rates():
    """Test common baud rates for TFT communication"""
    
    # Common baud rates for TFT displays
    baud_rates = [250000, 115200, 57600, 38400, 19200, 9600]
    port = config.TFT32_SERIAL_PORT
    
    print("🔍 Testing Different Baud Rates")
    print(f"📡 Port: {port}")
    print("=" * 50)
    
    for baud in baud_rates:
        print(f"\n🧪 Testing {baud} baud...")
        
        try:
            ser = serial.Serial(port, baud, timeout=1)
            print(f"✅ Opened at {baud} baud")
            print("📡 Listening for 8 seconds...")
            print("🎮 Send M105 from TFT Terminal NOW!")
            
            start_time = time.time()
            total_bytes = 0
            
            while time.time() - start_time < 8:
                if ser.in_waiting > 0:
                    data = ser.read(ser.in_waiting)
                    total_bytes += len(data)
                    print(f"📥 RECEIVED ({len(data)} bytes): {data}")
                    try:
                        text = data.decode('utf-8', errors='replace').strip()
                        print(f"📝 AS TEXT: '{text}'")
                        if 'M105' in text or 'N' in text:
                            print(f"🎯 FOUND TFT COMMAND! Baud rate {baud} works!")
                    except:
                        pass
                time.sleep(0.1)
            
            ser.close()
            
            if total_bytes > 0:
                print(f"✅ Received {total_bytes} bytes at {baud} baud")
                print(f"🎯 UPDATE config.py: TFT32_BAUDRATE = {baud}")
            else:
                print(f"❌ No data at {baud} baud")
                
        except Exception as e:
            print(f"❌ Error at {baud} baud: {e}")
    
    print("\n" + "=" * 50)
    print("🎯 Test complete!")
    print("📝 Update config.py with working baud rate if found")

if __name__ == "__main__":
    test_baud_rates() 