#!/usr/bin/env python3
"""
TFT32 Connection Bypass - RepRap Firmware Protocol
Based on BIGTREETECH firmware analysis for RRF configuration
"""

import serial
import time
import config

def bypass_connection():
    """Send responses in RepRap Firmware format expected by BIGTREETECH firmware"""
    
    print("🚀 TFT32 Connection Bypass - RepRap Firmware Protocol")
    print("🔍 Based on Mainboard_AckHandler.c analysis for RRF")
    print("🎯 Using RepRap format (NO @ symbol in temperature)")
    print("=" * 60)
    
    port = config.TFT32_SERIAL_PORT  
    baudrate = config.TFT32_BAUDRATE
    
    try:
        ser = serial.Serial(port, baudrate, timeout=1)
        print(f"✅ Connected to {port} at {baudrate} baud")
        print("⏱️  Sending CRITICAL first response for RepRap connection...")
        print()
        
        # CRITICAL: For RepRap Firmware, temperature response should NOT contain @
        # From line 409: if (!ack_seen("@"))  // it's RepRapFirmware
        # This means RRF responses should NOT have @ symbol
        
        first_response = "T:25.0 /0.0 B:22.0 /0.0"
        ser.write(f"{first_response}\r\n".encode())
        ser.flush()
        print(f"📤 CRITICAL FIRST (RRF): {first_response}")
        print("   ^ RepRap format (NO @ symbol) should trigger connection")
        
        time.sleep(0.5)
        
        # Send RepRap firmware identification
        firmware_response = "FIRMWARE_NAME:RepRapFirmware for Duet 2 WiFi FIRMWARE_VERSION:3.4.0 ELECTRONICS:Duet WiFi 1.02 or later FIRMWARE_DATE:2021-12-25"
        ser.write(f"{firmware_response}\r\n".encode())
        ser.flush()
        print(f"📤 FIRMWARE (RRF): {firmware_response[:50]}...")
        
        time.sleep(0.2)
        
        # Send basic OK
        ser.write(b"ok\r\n")
        ser.flush()
        print("📤 INITIAL: ok")
        
        print("\n🔄 Starting RepRap communication loop...")
        print("📺 TFT should now show CONNECTED status!")
        print("🎮 Try pressing buttons on TFT...")
        print()
        
        counter = 0
        while True:
            counter += 1
            
            # Handle incoming commands (what TFT sends to us)
            if ser.in_waiting > 0:
                incoming = ser.readline().decode('utf-8', errors='ignore').strip()
                print(f"📥 TFT COMMAND: '{incoming}'")
                
                # Respond based on RepRap firmware format
                if incoming.startswith('M105'):  # Temperature request
                    # RepRap format: NO @ symbol
                    response = "T:25.0 /0.0 B:22.0 /0.0"
                    ser.write(f"{response}\r\n".encode())
                    print(f"📤 M105 RESPONSE (RRF): {response}")
                    
                elif incoming.startswith('M115'):  # Firmware request
                    ser.write(f"{firmware_response}\r\n".encode())
                    print(f"📤 M115 RESPONSE (RRF): RepRap firmware info")
                    
                elif incoming.startswith('M114'):  # Position request
                    response = "X:150.00 Y:150.00 Z:10.00 E:0.00"
                    ser.write(f"{response}\r\n".encode())
                    print(f"📤 M114 RESPONSE (RRF): {response}")
                    
                elif incoming.startswith('M104') or incoming.startswith('M109'):  # Set hotend temp
                    print(f"🔥 HOTEND TEMP COMMAND: {incoming}")
                    ser.write(b"ok\r\n")
                    print(f"📤 RESPONSE: ok")
                    
                elif incoming.startswith('M140') or incoming.startswith('M190'):  # Set bed temp
                    print(f"🛏️ BED TEMP COMMAND: {incoming}")
                    ser.write(b"ok\r\n")
                    print(f"📤 RESPONSE: ok")
                    
                elif incoming.startswith('G28'):  # Home
                    print(f"🏠 HOME COMMAND: {incoming}")
                    ser.write(b"ok\r\n")
                    print(f"📤 RESPONSE: ok")
                    
                elif incoming.startswith('M92'):  # Steps per mm (sent by RRF detection)
                    response = "M92 X80.00 Y80.00 Z400.00 E420.00"
                    ser.write(f"{response}\r\n".encode())
                    print(f"📤 M92 RESPONSE (RRF): {response}")
                    
                else:
                    print(f"❓ OTHER COMMAND: {incoming}")
                    ser.write(b"ok\r\n")
                    print(f"📤 RESPONSE: ok")
            
            # Send periodic temperature updates (every 2 seconds) - RepRap format
            if counter % 20 == 0:  # Every 2 seconds (20 * 0.1s)
                temp_response = "T:25.0 /0.0 B:22.0 /0.0"  # NO @ symbol for RRF
                ser.write(f"{temp_response}\r\n".encode())
                print(f"🔄 PERIODIC (RRF): {temp_response}")
            
            time.sleep(0.1)
            
    except KeyboardInterrupt:
        print("\n🛑 Bypass stopped by user")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        if 'ser' in locals():
            ser.close()
            print("🔌 Serial connection closed")

if __name__ == "__main__":
    bypass_connection() 