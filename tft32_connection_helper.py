#!/usr/bin/env python3
"""
TFT32 Connection Helper
Establishes initial connection with TFT32 by sending proper handshake sequence
"""

import serial
import time
import argparse
import config

def establish_connection(port=None, baudrate=None, timeout=30):
    """
    Establish connection with TFT32 by sending the required initial responses
    
    Args:
        port: Serial port (default from config)
        baudrate: Baud rate (default from config) 
        timeout: Timeout in seconds (default: 30)
    """
    port = port or config.TFT32_SERIAL_PORT
    baudrate = baudrate or config.TFT32_BAUDRATE
    
    print(f"🔗 TFT32 Connection Helper")
    print(f"🎯 Goal: Establish connection and fix 'no printer attached' status")
    print(f"📡 Port: {port}")
    print(f"⚡ Baud: {baudrate}")
    print(f"⏱️  Timeout: {timeout}s")
    print()
    
    try:
        ser = serial.Serial(
            port, 
            baudrate, 
            timeout=1,
            write_timeout=2
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
                # RepRap Firmware format: NO @ symbol (firmware detects RRF by absence of @)
                if response_count % 5 == 0:  # Every ~1 second  
                    ser.write(b"T:25.0 /0.0 B:22.0 /0.0\r\n")
                    ser.flush()
                    print(f"🌡️ Sent connection temperature (RepRap format)")
                
                # Send firmware identification periodically
                if response_count % 10 == 0:  # Every ~2 seconds
                    ser.write(b"FIRMWARE_NAME:RepRapFirmware for Duet 2 WiFi FIRMWARE_VERSION:3.4.0\r\n")
                    ser.flush()
                    print(f"📤 Sent RepRap firmware ID")
                
                # Always send OK response
                ser.write(b"ok\r\n")
                ser.flush()
                
                # Read any incoming data
                if ser.in_waiting > 0:
                    incoming = ser.readline().decode('utf-8', errors='ignore').strip()
                    if incoming:
                        print(f"📥 TFT >> PI: '{incoming}'")
                        
                        # Respond to specific commands with proper format
                        if incoming.startswith('M105'):  # Temperature request
                            response = b"T:25.0 /0.0 B:22.0 /0.0\r\n"
                            ser.write(response)
                            ser.flush()
                            print(f"📤 PI >> TFT: '{response.decode().strip()}'")
                        elif incoming.startswith('M115'):  # Firmware request
                            response = b"FIRMWARE_NAME:RepRapFirmware for Duet 2 WiFi FIRMWARE_VERSION:3.4.0\r\n"
                            ser.write(response)
                            ser.flush()
                            print(f"📤 PI >> TFT: '{response.decode().strip()}'")
                        elif incoming.startswith('M92'):   # Steps per mm request
                            response = b"M92 X80.00 Y80.00 Z400.00 E420.00\r\n"
                            ser.write(response)
                            ser.flush()
                            print(f"📤 PI >> TFT: '{response.decode().strip()}'")
                        elif incoming.startswith('M114'):  # Position request
                            response = b"X:150.00 Y:150.00 Z:10.00 E:0.00\r\n"
                            ser.write(response)
                            ser.flush()
                            print(f"📤 PI >> TFT: '{response.decode().strip()}'")
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
    parser = argparse.ArgumentParser(description="TFT32 Connection Helper - Establish TFT connection")
    parser.add_argument("--port", default=config.TFT32_SERIAL_PORT, 
                       help=f"Serial port (default: {config.TFT32_SERIAL_PORT})")
    parser.add_argument("--baud", type=int, default=config.TFT32_BAUDRATE, 
                       help=f"Baud rate (default: {config.TFT32_BAUDRATE})")
    parser.add_argument("--timeout", type=int, default=30, help="Connection timeout in seconds (default: 30)")
    
    args = parser.parse_args()
    
    try:
        establish_connection(args.port, args.baud, args.timeout)
    except KeyboardInterrupt:
        print("\n🛑 Connection helper stopped by user")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main() 