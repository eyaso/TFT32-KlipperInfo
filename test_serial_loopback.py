#!/usr/bin/env python3
"""
Test serial communication loopback
"""

import serial
import time

def test_loopback():
    port = "/dev/ttyS0"
    baudrate = 115200
    
    print(f"🔗 Testing serial loopback on {port} at {baudrate} baud")
    print("⚠️  IMPORTANT: Connect Pin 8 to Pin 10 on Raspberry Pi for this test!")
    print("   (GPIO 14 TX to GPIO 15 RX)")
    print()
    
    try:
        ser = serial.Serial(port, baudrate, timeout=2)
        print("✅ Serial port opened")
        
        test_messages = [
            "test1",
            "M105", 
            "hello"
        ]
        
        for msg in test_messages:
            print(f"📤 Sending: '{msg}'")
            ser.write(f"{msg}\r\n".encode())
            ser.flush()
            
            time.sleep(0.1)
            
            if ser.in_waiting > 0:
                received = ser.readline().decode('utf-8', errors='ignore').strip()
                print(f"📥 Received: '{received}'")
                if received == msg:
                    print("✅ Loopback OK")
                else:
                    print("⚠️  Data mismatch")
            else:
                print("❌ No response received")
            print()
        
        ser.close()
        print("🔌 Serial port closed")
        
    except Exception as e:
        print(f"❌ Error: {e}")

def test_tft_communication():
    port = "/dev/ttyS0"
    baudrate = 115200
    
    print(f"🔗 Testing TFT communication on {port}")
    print("📺 Remove loopback wire and connect to TFT")
    print("⏱️  Will listen for 10 seconds...")
    print()
    
    try:
        ser = serial.Serial(port, baudrate, timeout=1)
        print("✅ Serial port opened")
        
        start_time = time.time()
        while time.time() - start_time < 10:
            # Send temperature every 2 seconds
            if int(time.time() - start_time) % 2 == 0:
                msg = "ok T:25.0 /0.0 B:22.0 /0.0 @:0 B@:0\r\n"
                ser.write(msg.encode())
                ser.flush()
                print(f"📤 Sent: {msg.strip()}")
            
            # Check for incoming data
            if ser.in_waiting > 0:
                received = ser.readline().decode('utf-8', errors='ignore').strip()
                print(f"📥 TFT says: '{received}'")
            
            time.sleep(0.5)
        
        ser.close()
        print("🔌 Test complete")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    print("🧪 Serial Communication Test")
    print("=" * 40)
    
    choice = input("Choose test:\n1. Loopback test (connect Pin 8 to Pin 10)\n2. TFT communication test\nEnter 1 or 2: ")
    
    if choice == "1":
        test_loopback()
    elif choice == "2":
        test_tft_communication()
    else:
        print("Invalid choice") 