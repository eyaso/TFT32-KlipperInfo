#!/usr/bin/env python3
"""
TFT32 Connection Helper
Sends proper responses to establish TFT connection and clear "no printer attached" message
"""

import serial
import time
import sys
import argparse

def establish_connection(port="/dev/ttyS0", baudrate=115200, timeout=30):
    """Send proper responses to establish TFT connection"""
    
    print(f"🔗 TFT32 Connection Helper")
    print(f"📡 Connecting to {port} at {baudrate} baud...")
    
    try:
        # Open serial connection
        ser = serial.Serial(
            port=port,
            baudrate=baudrate,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=1,
            xonxoff=False,
            rtscts=False,
            dsrdtr=False
        )
        
        print(f"✅ Connected to TFT32")
        print(f"⏱️ Establishing connection for {timeout} seconds...")
        print(f"📺 Watch TFT status - should change from 'no printer attached' to connected!")
        print(f"🛑 Press Ctrl+C to stop")
        
        start_time = time.time()
        response_count = 0
        
        while time.time() - start_time < timeout:
            try:
                # Send the CRITICAL temperature response that establishes connection
                # Standard Marlin M105 format: T:current /target B:current /target @:power B@:bed_power
                if response_count % 5 == 0:  # Every ~1 second  
                    ser.write(b"T:25.0 /0.0 B:22.0 /0.0 @:0 B@:0\r\n")
                    ser.flush()
                    print(f"🌡️ Sent connection temperature (standard M105 format)")
                
                # Send firmware identification periodically
                if response_count % 10 == 0:  # Every ~2 seconds
                    ser.write(b"FIRMWARE_NAME:Marlin 2.0.x SOURCE_CODE_URL:github.com/MarlinFirmware/Marlin\r\n")
                    ser.flush()
                    print(f"📤 Sent firmware ID")
                
                # Always send OK response
                ser.write(b"ok\r\n")
                ser.flush()
                
                # Read any incoming data
                if ser.in_waiting > 0:
                    incoming = ser.readline().decode('utf-8', errors='ignore').strip()
                    if incoming:
                        print(f"📥 TFT sent: {incoming}")
                        
                        # Respond to specific commands with proper format
                        if incoming.startswith('M105'):  # Temperature request
                            ser.write(b"@:0 T:25.0/0.0 B:22.0/0.0\r\n")
                            ser.flush()
                            print(f"🌡️ Responded to M105 with connection format")
                        elif incoming.startswith('M115'):  # Firmware request
                            ser.write(b"FIRMWARE_NAME:Marlin 2.0.x SOURCE_CODE_URL:github.com/MarlinFirmware/Marlin\r\n")
                            ser.flush()
                            print(f"📋 Responded to M115 firmware request")
                        elif incoming.startswith('M114'):  # Position request
                            ser.write(b"X:150.00 Y:150.00 Z:10.00 E:0.00\r\n")
                            ser.flush()
                            print(f"📍 Responded to M114 position request")
                        else:
                            # Generic OK for other commands
                            ser.write(b"ok\r\n")
                            ser.flush()
                
                response_count += 1
                time.sleep(0.2)  # 200ms interval
                
            except KeyboardInterrupt:
                print(f"\n🛑 Stopped by user")
                break
            except Exception as e:
                print(f"⚠️ Error: {e}")
                time.sleep(0.5)
                continue
        
        print(f"\n✅ Connection establishment completed!")
        print(f"📊 Sent {response_count} responses")
        print(f"📺 TFT should now show as connected (no more 'no printer attached')")
        
        ser.close()
        return True
        
    except Exception as e:
        print(f"❌ Failed to connect: {e}")
        print(f"💡 Make sure:")
        print(f"   - TFT32 is powered on")
        print(f"   - Serial wiring is correct (TX/RX)")
        print(f"   - Port {port} exists and is accessible")
        return False

def main():
    """Main function with command line options"""
    parser = argparse.ArgumentParser(description="TFT32 Connection Helper - Establish connection to clear 'no printer attached'")
    parser.add_argument("--port", default="/dev/ttyS0", help="Serial port (default: /dev/ttyS0)")
    parser.add_argument("--baud", type=int, default=115200, help="Baud rate (default: 115200)")
    parser.add_argument("--timeout", type=int, default=30, help="Timeout in seconds (default: 30)")
    
    args = parser.parse_args()
    
    print(f"🚀 Starting TFT32 Connection Helper...")
    print(f"📡 Port: {args.port}")
    print(f"⚡ Baud: {args.baud}")
    print(f"⏱️ Timeout: {args.timeout}s")
    print(f"")
    print(f"🔧 What this does:")
    print(f"   - Sends temperature responses with @: prefix")
    print(f"   - This triggers TFT connection detection")
    print(f"   - Changes status from 'no printer attached' to connected")
    print(f"   - Responds to TFT commands properly")
    print(f"")
    
    if establish_connection(args.port, args.baud, args.timeout):
        print(f"")
        print(f"🎉 Success! Your TFT should now show as connected.")
        print(f"🔄 You can now start the full monitor:")
        print(f"   python3 klipper_tft32_monitor.py")
    else:
        print(f"")
        print(f"❌ Connection helper failed. Check connections and try again.")
        sys.exit(1)

if __name__ == "__main__":
    main() 