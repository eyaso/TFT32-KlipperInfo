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
        print("⏱️  Waiting for TFT to send initial M105 probe...")
        print("   (TFT should send M105 within a few seconds of boot)")
        print()
        
        # RepRap firmware identification for when requested
        firmware_response = "FIRMWARE_NAME:RepRapFirmware for Duet 2 WiFi FIRMWARE_VERSION:3.4.0 ELECTRONICS:Duet WiFi 1.02 or later FIRMWARE_DATE:2021-12-25"
        
        print("\n🔄 Starting RepRap communication loop...")
        print("📺 Waiting for TFT to initiate connection...")
        print("🎮 Try pressing buttons on TFT...")
        print()
        print("⚠️  CRITICAL: Looking for TFT's INITIAL M105 probe...")
        print("   If TFT rebooted, it should send M105 within a few seconds...")
        print()
        
        counter = 0
        initial_probe_detected = False
        
        while True:
            counter += 1
            
            # Handle incoming commands (what TFT sends to us)
            if ser.in_waiting > 0:
                incoming = ser.readline().decode('utf-8', errors='ignore').strip()
                print(f"📥 TFT COMMAND: '{incoming}'")
                
                # Detect the CRITICAL initial M105 probe
                if incoming.startswith('M105') and not initial_probe_detected:
                    initial_probe_detected = True
                    print("🎯 DETECTED INITIAL M105 PROBE FROM TFT!")
                    print("🔄 This is the connection detection moment...")
                    
                    # Send the CRITICAL RepRap connection response
                    # Line 389 requires: T0: or T:0 (not just T:) for RepRap firmware
                    response = "T:0 /0.0 B:22.0 /0.0"  # T:0 format for RRF
                    ser.write(f"{response}\r\n".encode())
                    print(f"📤 CRITICAL CONNECTION RESPONSE: {response}")
                    print("   ^ T:0 format required for RepRap connection detection")
                    
                    # Send firmware ID immediately after
                    time.sleep(0.1)
                    ser.write(f"{firmware_response}\r\n".encode())
                    print(f"📤 FIRMWARE FOLLOWUP: RepRap firmware info")
                    
                    continue
                
                # Respond based on RepRap firmware format
                if incoming.startswith('M105'):  # Temperature request
                    # RepRap format: T:0 (line 389 requirement)
                    response = "T:0 /0.0 B:22.0 /0.0"
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