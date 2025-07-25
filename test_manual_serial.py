#!/usr/bin/env python3
"""
Manual Serial Test - Test if Pi can receive data from TFT terminal
"""

import serial
import time
import threading

def listen_for_data(ser):
    """Listen for incoming data"""
    print("🔊 Listening for data... (Type commands in TFT terminal)")
    
    while True:
        try:
            if ser.in_waiting > 0:
                # Try multiple read methods
                bytes_available = ser.in_waiting
                print(f"\n📊 {bytes_available} bytes available")
                
                # Method 1: readline
                try:
                    line_data = ser.readline().decode('utf-8', errors='ignore').strip()
                    if line_data:
                        print(f"📥 READLINE: '{line_data}'")
                except Exception as e:
                    print(f"❌ READLINE failed: {e}")
                
                # Method 2: read all available bytes
                try:
                    ser.reset_input_buffer()  # Reset position
                    raw_data = ser.read(bytes_available)
                    if raw_data:
                        print(f"🔧 RAW: {raw_data}")
                        decoded = raw_data.decode('utf-8', errors='ignore')
                        print(f"📝 DECODED: '{decoded}'")
                except Exception as e:
                    print(f"❌ RAW READ failed: {e}")
            
            time.sleep(0.1)
            
        except KeyboardInterrupt:
            print("\n🛑 Stopping listener...")
            break
        except Exception as e:
            print(f"❌ Error: {e}")
            time.sleep(1)

def send_test_data(ser):
    """Send test data to TFT"""
    print("\n📤 Sending test responses to TFT...")
    
    test_responses = [
        "ok T:25.0 /0.0 B:22.0 /0.0 @:0 B@:0",
        "FIRMWARE_NAME:Marlin 2.1.0 TEST",
        "ok",
        "X:150.00 Y:150.00 Z:10.00 E:0.00"
    ]
    
    for response in test_responses:
        ser.write(f"{response}\r\n".encode())
        ser.flush()
        print(f"   Sent: {response}")
        time.sleep(0.5)

def main():
    try:
        # Load config
        import config
        port = config.TFT32_SERIAL_PORT
        baudrate = config.TFT32_BAUDRATE
    except:
        port = '/dev/ttyS0'
        baudrate = 115200
    
    print(f"🔍 Manual Serial Test")
    print(f"📡 Port: {port} at {baudrate} baud")
    print("=" * 50)
    
    try:
        ser = serial.Serial(port, baudrate, timeout=1)
        print(f"✅ Serial port opened")
        
        # Start listener in background
        listener_thread = threading.Thread(target=listen_for_data, args=(ser,), daemon=True)
        listener_thread.start()
        
        # Send some test data
        send_test_data(ser)
        
        # Keep listening
        print("\n💡 Now try typing commands in your TFT terminal")
        print("   Examples: M105, M115, M114")
        print("   Press Ctrl+C to stop")
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n🛑 Stopping...")
        
        ser.close()
        
    except Exception as e:
        print(f"❌ Failed: {e}")

if __name__ == "__main__":
    main()
