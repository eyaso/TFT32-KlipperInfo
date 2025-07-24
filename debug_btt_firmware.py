#!/usr/bin/env python3
"""
Debug script to see what BIGTREETECH firmware is sending
"""

import serial
import time
import logging

def debug_btt_communication():
    """Debug communication with BIGTREETECH firmware"""
    try:
        import config
        serial_port = getattr(config, 'TFT32_SERIAL_PORT', '/dev/ttyS0')
        baudrate = getattr(config, 'TFT32_BAUDRATE', 250000)
    except ImportError:
        serial_port = '/dev/ttyS0'
        baudrate = 250000
    
    print("🔍 BIGTREETECH Firmware Debug")
    print("=" * 50)
    print(f"📡 Port: {serial_port} at {baudrate} baud")
    print("🎯 Looking for incoming TFT commands...")
    print("💡 Press Ctrl+C to stop")
    print()
    
    try:
        ser = serial.Serial(
            port=serial_port,
            baudrate=baudrate,
            timeout=1,
            write_timeout=1
        )
        
        print("✅ Serial connected, listening...")
        print("📱 Try using TFT controls now...")
        print()
        
        command_count = 0
        last_command_time = time.time()
        
        while True:
            if ser.in_waiting > 0:
                try:
                    incoming = ser.readline().decode('utf-8', errors='ignore').strip()
                    if incoming:
                        command_count += 1
                        current_time = time.time()
                        time_since_last = current_time - last_command_time
                        last_command_time = current_time
                        
                        print(f"📥 [{command_count:03d}] (+{time_since_last:.1f}s) TFT >> PI: '{incoming}'")
                        
                        # Send appropriate response
                        response = get_response_for_command(incoming)
                        if response:
                            ser.write(f"{response}\r\n".encode())
                            ser.flush()
                            print(f"📤 [{command_count:03d}] PI >> TFT: '{response}'")
                        
                        print()
                        
                except Exception as e:
                    print(f"❌ Decode error: {e}")
            
            time.sleep(0.1)
            
    except KeyboardInterrupt:
        print(f"\n🛑 Stopped. Received {command_count} commands total.")
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
        return "X:150.00 Y:150.00 Z:10.00 E:0.00"
    elif 'M27' in command:
        return "Not SD printing"
    elif 'M20' in command:
        return "Begin file list\ntest.gcode\nEnd file list"
    elif 'M92' in command:
        return "M92 X80.00 Y80.00 Z400.00 E420.00"
    elif command.startswith('M104') or command.startswith('M109'):
        return "ok"
    elif command.startswith('M140') or command.startswith('M190'):
        return "ok"
    elif command.startswith('G28'):
        return "ok"
    elif command.strip() == "":
        return None
    else:
        return "ok"

if __name__ == "__main__":
    debug_btt_communication() 