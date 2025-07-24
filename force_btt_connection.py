#!/usr/bin/env python3
"""
Force BIGTREETECH firmware connection with complete handshake
"""

import serial
import time
import logging

def force_btt_connection():
    """Send complete BIGTREETECH handshake sequence"""
    try:
        import config
        serial_port = getattr(config, 'TFT32_SERIAL_PORT', '/dev/ttyS0')
        baudrate = getattr(config, 'TFT32_BAUDRATE', 250000)
    except ImportError:
        serial_port = '/dev/ttyS0'
        baudrate = 250000
    
    print("🔧 Force BIGTREETECH Connection")
    print("=" * 50)
    print(f"📡 Port: {serial_port} at {baudrate} baud")
    print("🎯 Sending aggressive BIGTREETECH handshake...")
    print()
    
    try:
        ser = serial.Serial(
            port=serial_port,
            baudrate=baudrate,
            timeout=1,
            write_timeout=1
        )
        
        print("✅ Serial connected")
        
        # Complete BIGTREETECH handshake sequence
        handshake_sequence = [
            # Initial temperature response (critical for connection)
            "ok T:25.0 /0.0 B:22.0 /0.0 @:0 B@:0",
            
            # Firmware identification
            "FIRMWARE_NAME:Klipper HOST_ACTION_COMMANDS:1 EXTRUDER_COUNT:1",
            
            # Capabilities (what BTT firmware expects)
            "Cap:EEPROM:1",
            "Cap:AUTOREPORT_TEMP:1", 
            "Cap:HOST_ACTION_COMMANDS:1",
            "Cap:PROMPT_SUPPORT:1",
            "Cap:AUTOLEVEL:1",
            "Cap:RUNOUT:1",
            "Cap:Z_PROBE:1",
            "Cap:LEVELING_DATA:1",
            "Cap:BUILD_PERCENT:1",
            "Cap:SOFTWARE_POWER:1",
            "Cap:TOGGLE_LIGHTS:1",
            "Cap:CASE_LIGHT_BRIGHTNESS:1",
            "Cap:EMERGENCY_PARSER:1",
            
            # Machine settings
            "M92 X80.00 Y80.00 Z400.00 E420.00",
            "M203 X500.00 Y500.00 Z10.00 E120.00",
            "M201 X3000.00 Y3000.00 Z100.00 E10000.00",
            "M205 X8.00 Y8.00 Z0.40 E5.00",
            "M206 X0.00 Y0.00 Z0.00",
            
            # Status responses
            "X:150.00 Y:150.00 Z:10.00 E:0.00",
            "Not SD printing",
            
            # Final OK
            "ok"
        ]
        
        print("📤 Sending handshake sequence...")
        for i, response in enumerate(handshake_sequence):
            print(f"📤 [{i+1:02d}/{len(handshake_sequence)}] {response}")
            ser.write(f"{response}\r\n".encode())
            ser.flush()
            time.sleep(0.2)  # Wait between responses
        
        print("\n✅ Handshake complete!")
        print("🔍 Now listening for TFT commands...")
        print("📱 Try using TFT controls...")
        print("💡 Press Ctrl+C to stop")
        print()
        
        # Listen for responses
        command_count = 0
        start_time = time.time()
        
        while True:
            if ser.in_waiting > 0:
                try:
                    incoming = ser.readline().decode('utf-8', errors='ignore').strip()
                    if incoming:
                        command_count += 1
                        elapsed = time.time() - start_time
                        print(f"📥 [{command_count:03d}] (+{elapsed:.1f}s) TFT >> PI: '{incoming}'")
                        
                        # Send appropriate response
                        response = get_response_for_command(incoming)
                        if response:
                            ser.write(f"{response}\r\n".encode())
                            ser.flush()
                            print(f"📤 [{command_count:03d}] PI >> TFT: '{response}'")
                        
                        print()
                        
                except Exception as e:
                    print(f"❌ Decode error: {e}")
            
            # Send periodic temperature updates
            current_time = time.time()
            if int(current_time) % 5 == 0 and (current_time - int(current_time)) < 0.1:
                temp_response = "ok T:25.5 /0.0 B:22.3 /0.0 @:0 B@:0"
                ser.write(f"{temp_response}\r\n".encode())
                ser.flush()
                print(f"📤 [AUTO] Periodic temperature: {temp_response}")
            
            time.sleep(0.1)
            
    except KeyboardInterrupt:
        print(f"\n🛑 Stopped. Received {command_count} commands total.")
        if command_count == 0:
            print("\n⚠️  NO COMMANDS RECEIVED!")
            print("🔧 Possible issues:")
            print("   • TFT firmware not sending commands")
            print("   • Wrong serial port or baud rate")
            print("   • TFT in wrong mode")
            print("   • Hardware connection issue")
        else:
            print(f"\n✅ Success! TFT sent {command_count} commands")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        if 'ser' in locals():
            ser.close()

def get_response_for_command(command):
    """Get appropriate response for command"""
    if 'M105' in command:
        return "ok T:25.5 /0.0 B:22.3 /0.0 @:0 B@:0"
    elif 'M115' in command:
        return "FIRMWARE_NAME:Klipper HOST_ACTION_COMMANDS:1 EXTRUDER_COUNT:1"
    elif 'M114' in command:
        return "ok\nX:150.00 Y:150.00 Z:10.00 E:0.00"
    elif 'M27' in command:
        return "Not SD printing"
    elif 'M20' in command:
        return "Begin file list\ntest.gcode\nEnd file list"
    elif 'M92' in command:
        return "ok\nM92 X80.00 Y80.00 Z400.00 E420.00"
    elif command.startswith('M104') or command.startswith('M109'):
        return "ok"
    elif command.startswith('M140') or command.startswith('M190'):
        return "ok"
    elif command.startswith('G28'):
        return "ok"
    elif 'N' in command and '*' in command:  # Line number with checksum
        return "ok"
    elif command.strip() == "":
        return None
    else:
        return "ok"

if __name__ == "__main__":
    force_btt_connection() 