#!/usr/bin/env python3
"""
Simple startup script for TFT32 Dual Protocol Client
Run this to start the working TFT32 connection
"""

import asyncio
import logging
import sys
import os

# Add current directory to path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dual_protocol_tft import DualProtocolTFT

def setup_logging():
    """Setup logging configuration"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('tft32_client.log')
        ]
    )

async def main():
    """Main function"""
    print("🚀 Starting TFT32 Dual Protocol Client")
    print("=" * 50)
    
    setup_logging()
    
    # Create client instance
    client = DualProtocolTFT()
    
    try:
        print(f"📡 Connecting to {client.serial_port} at {client.baudrate} baud...")
        print("🔍 Auto-detecting firmware type...")
        
        # Connect and detect firmware
        if await client.connect_and_detect():
            print(f"✅ Connected! Firmware: {client.firmware_type.value}")
            print("📱 TFT should show temperature values (25.0°C, 22.0°C)")
            print("🎮 Try using TFT controls (they should work now)")
            print("📊 Real data from Moonraker will be displayed")
            print("📤 KLIP messages show comprehensive data being sent")
            print("\n💡 Press Ctrl+C to stop")
            
            # Start communication and update loops
            await asyncio.gather(
                client.communication_loop(),
                client.update_loop()
            )
        else:
            print("❌ Failed to connect to TFT32")
            print("🔧 Check serial port, baud rate, and wiring")
            return 1
            
    except KeyboardInterrupt:
        print("\n🛑 Shutting down TFT32 client...")
    except Exception as e:
        print(f"❌ Error: {e}")
        logging.exception("Unexpected error occurred")
        return 1
    finally:
        await client.close()
        print("✅ Client stopped cleanly")
    
    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 