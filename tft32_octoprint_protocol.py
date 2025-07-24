#!/usr/bin/env python3
"""
TFT32 OctoPrint Protocol - Based on BTT Touch Support Plugin
Uses the exact same protocol as the OctoPrint BTT plugin
"""

import serial
import time
import config

def octoprint_protocol():
    """Use OctoPrint BTT Touch Support protocol"""
    
    print("🐙 TFT32 OctoPrint Protocol Test")
    print("🔍 Based on BTT Touch Support Plugin")
    print("🎯 Using M118 P0 A1 action: format")
    print("=" * 60)
    
    port = config.TFT32_SERIAL_PORT  
    baudrate = config.TFT32_BAUDRATE
    serial_port_nr = 0  # Default from plugin
    
    try:
        ser = serial.Serial(port, baudrate, timeout=1)
        print(f"✅ Connected to {port} at {baudrate} baud")
        print("⏱️  Waiting for TFT to send initial commands...")
        print("🎮 Go to TFT Terminal and send M105 or other commands")
        print()
        
        counter = 0
        initial_contact = False
        
        while True:
            counter += 1
            
            # Handle incoming commands from TFT
            if ser.in_waiting > 0:
                incoming = ser.readline().decode('utf-8', errors='ignore').strip()
                print(f"📥 TFT >> PI: '{incoming}'")
                
                if not initial_contact and any(cmd in incoming for cmd in ['M105', 'M115', 'M92']):
                    initial_contact = True
                    print("🎯 INITIAL CONTACT ESTABLISHED!")
                    
                    # Send initial setup responses
                    print("📤 Sending initial setup sequence...")
                    
                    # M105 - Temperature response (standard format)
                    if 'M105' in incoming:
                        response = "ok T:25.0 /0.0 B:22.0 /0.0 @:0 B@:0"
                        ser.write(f"{response}\r\n".encode())
                        print(f"📤 TEMP: {response}")
                    
                    # M115 - Firmware info
                    elif 'M115' in incoming:
                        response = "FIRMWARE_NAME:Klipper HOST_ACTION_COMMANDS:1 EXTRUDER_COUNT:1"
                        ser.write(f"{response}\r\n".encode())
                        print(f"📤 FIRMWARE: {response}")
                        
                        # Send capabilities
                        capabilities = [
                            "Cap:EEPROM:1",
                            "Cap:AUTOREPORT_TEMP:1", 
                            "Cap:HOST_ACTION_COMMANDS:1",
                            "Cap:PROMPT_SUPPORT:1",
                        ]
                        for cap in capabilities:
                            ser.write(f"{cap}\r\n".encode())
                            print(f"📤 CAP: {cap}")
                        
                        ser.write(b"ok\r\n")
                        print(f"📤 OK")
                    
                    # M92 - Steps per mm
                    elif 'M92' in incoming:
                        response = "M92 X80.00 Y80.00 Z400.00 E420.00"
                        ser.write(f"{response}\r\n".encode())
                        print(f"📤 STEPS: {response}")
                        ser.write(b"ok\r\n")
                
                # Handle regular commands
                elif 'M105' in incoming:  # Temperature request
                    response = "ok T:25.0 /0.0 B:22.0 /0.0 @:0 B@:0"
                    ser.write(f"{response}\r\n".encode())
                    print(f"📤 TEMP: {response}")
                
                elif 'M115' in incoming:  # Firmware request
                    response = "FIRMWARE_NAME:Klipper HOST_ACTION_COMMANDS:1 EXTRUDER_COUNT:1"
                    ser.write(f"{response}\r\n".encode())
                    print(f"📤 FIRMWARE: {response}")
                    ser.write(b"ok\r\n")
                
                elif 'M114' in incoming:  # Position request
                    response = "X:150.00 Y:150.00 Z:10.00 E:0.00 Count X:12000 Y:12000 Z:4000"
                    ser.write(f"{response}\r\n".encode())
                    print(f"📤 POSITION: {response}")
                    ser.write(b"ok\r\n")
                
                else:
                    # Standard OK response
                    ser.write(b"ok\r\n")
                    print(f"📤 OK")
            
            # Send periodic OctoPrint-style notifications (every 5 seconds)
            if initial_contact and counter % 50 == 0:  # Every 5 seconds
                print("📡 Sending OctoPrint-style notifications...")
                
                # Time notification
                time_cmd = f"M118 P{serial_port_nr} A1 action:notification Time Left 01h23m45s"
                ser.write(f"{time_cmd}\r\n".encode())
                print(f"📤 TIME: {time_cmd}")
                
                # Progress notification  
                progress_cmd = f"M118 P{serial_port_nr} A1 action:notification Data Left 75/100"
                ser.write(f"{progress_cmd}\r\n".encode())
                print(f"📤 PROGRESS: {progress_cmd}")
            
            time.sleep(0.1)
            
    except KeyboardInterrupt:
        print("\n🛑 Protocol test stopped by user")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        if 'ser' in locals():
            ser.close()
            print("🔌 Serial connection closed")

if __name__ == "__main__":
    octoprint_protocol() 