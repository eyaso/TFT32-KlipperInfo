#!/usr/bin/env python3
"""
Simple startup script for TFT32 Moonraker Plugin
Run this to test the plugin in standalone mode
"""

import asyncio
import logging
import sys
import os

# Add current directory to path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from moonraker_tft_plugin import TFT32Plugin

def setup_logging():
    """Setup logging configuration"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('tft32_plugin.log')
        ]
    )

async def main():
    """Main function"""
    print("🚀 Starting TFT32 Moonraker Plugin")
    print("=" * 50)
    
    setup_logging()
    
    # Create plugin instance
    plugin = TFT32Plugin()
    
    try:
        # Initialize the plugin
        await plugin.component_init()
        
        if plugin.connected:
            print("✅ TFT32 plugin started successfully!")
            print("📱 Check your TFT display - it should show 'Connected' status")
            print("🎮 Try using TFT controls (pause, resume, etc.)")
            print("📊 Plugin will send temperature and progress updates")
            print("\n💡 Press Ctrl+C to stop")
            
            # Keep running until interrupted
            while True:
                await asyncio.sleep(1)
        else:
            print("❌ Failed to connect to TFT32")
            print("🔧 Check serial port and wiring")
            return 1
            
    except KeyboardInterrupt:
        print("\n🛑 Shutting down TFT32 plugin...")
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1
    finally:
        await plugin.close()
        print("✅ Plugin stopped cleanly")
    
    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 