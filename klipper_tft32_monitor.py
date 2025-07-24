#!/usr/bin/env python3
"""
Klipper TFT32 Monitor using Serial Communication
Connects to Moonraker API and sends data to MKS TFT32 via serial
"""

import time
import logging
import signal
import sys
from threading import Event
import atexit

from moonraker_client import MoonrakerClient
from tft32_serial_client import TFT32SerialClient
import config

class KlipperTFT32Monitor:
    """Main application class for the Klipper TFT32 monitor"""
    
    def __init__(self):
        self.setup_logging()
        self.logger = logging.getLogger(__name__)
        
        # Initialize components
        self.moonraker = None
        self.tft32 = None
        self.running = Event()
        self.running.set()
        
        # Data storage
        self.last_temperatures = {}
        self.last_print_stats = {}
        self.last_comprehensive_data = {}
        self.connection_status = False
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        atexit.register(self.cleanup)
        
        self.logger.info("Klipper TFT32 Monitor starting...")
    
    def setup_logging(self):
        """Configure logging"""
        logging.basicConfig(
            level=getattr(logging, config.LOG_LEVEL),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(config.LOG_FILE),
                logging.StreamHandler(sys.stdout)
            ]
        )
    
    def initialize_components(self):
        """Initialize Moonraker client and TFT32 serial connection"""
        try:
            # Initialize Moonraker client
            self.logger.info(f"Connecting to Moonraker at {config.MOONRAKER_HOST}:{config.MOONRAKER_PORT}")
            self.moonraker = MoonrakerClient(
                host=config.MOONRAKER_HOST,
                port=config.MOONRAKER_PORT
            )
            
            # Test connection
            if not self.moonraker.is_connected():
                raise ConnectionError("Cannot connect to Moonraker")
            
            self.logger.info("Moonraker connection established")
            
            # Initialize TFT32 serial connection
            self.logger.info(f"Connecting to TFT32 on {config.TFT32_SERIAL_PORT}")
            self.tft32 = TFT32SerialClient(
                port=config.TFT32_SERIAL_PORT,
                baudrate=config.TFT32_BAUDRATE
            )
            
            if not self.tft32.connect():
                raise ConnectionError("Cannot connect to TFT32")
            
            self.logger.info("TFT32 serial connection established")
            
            # Give TFT32 time to initialize
            time.sleep(2)
            
            self.logger.info("Components initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize components: {e}")
            return False
    
    def update_data(self):
        """Update printer data from Moonraker and send to TFT32"""
        try:
            # Check connection
            self.connection_status = self.moonraker.is_connected()
            
            if self.connection_status:
                # Get comprehensive data for custom TFT screen
                comprehensive_data = self.moonraker.get_comprehensive_status()
                if comprehensive_data:
                    self.last_comprehensive_data = comprehensive_data
                    # Send comprehensive data to TFT32
                    if self.tft32 and self.tft32.is_connected():
                        self.tft32.update_comprehensive_data(comprehensive_data)
                
                # Still get individual data for backward compatibility
                temps = self.moonraker.get_temperatures()
                if temps:
                    self.last_temperatures = temps
                    # Send to TFT32 (this will be handled by comprehensive data now)
                    if self.tft32 and self.tft32.is_connected():
                        self.tft32.update_temperatures(temps)
                
                # Get print stats
                stats = self.moonraker.get_print_stats()
                if stats:
                    self.last_print_stats = stats
                    # Send to TFT32 (this will be handled by comprehensive data now)
                    if self.tft32 and self.tft32.is_connected():
                        self.tft32.update_print_status(stats)
            
        except Exception as e:
            self.logger.error(f"Error updating data: {e}")
            self.connection_status = False
    
    def main_loop(self):
        """Main monitoring loop"""
        self.logger.info("Starting main monitoring loop")
        self.logger.info("Enhanced comprehensive data collection enabled")
        
        last_update = 0
        last_connection_check = 0
        
        while self.running.is_set():
            try:
                current_time = time.time()
                
                # Update connection status periodically
                if current_time - last_connection_check >= config.CONNECTION_CHECK_INTERVAL:
                    self.connection_status = self.moonraker.is_connected() if self.moonraker else False
                    last_connection_check = current_time
                
                # Update data
                if current_time - last_update >= config.UPDATE_INTERVAL:
                    self.update_data()
                    last_update = current_time
                    
                    # Log comprehensive data status
                    if self.last_comprehensive_data:
                        self.logger.debug(f"Comprehensive data: State={self.last_comprehensive_data.get('state')}, "
                                        f"Progress={self.last_comprehensive_data.get('progress', 0):.1f}%, "
                                        f"Hotend={self.last_comprehensive_data.get('hotend_temp', 0):.1f}°C, "
                                        f"Bed={self.last_comprehensive_data.get('bed_temp', 0):.1f}°C")
                
                # Small sleep to prevent excessive CPU usage
                time.sleep(0.1)
                
            except KeyboardInterrupt:
                self.logger.info("Received keyboard interrupt")
                break
            except Exception as e:
                self.logger.error(f"Error in main loop: {e}")
                time.sleep(1)  # Wait before retrying
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        self.logger.info(f"Received signal {signum}, shutting down...")
        self.running.clear()
    
    def cleanup(self):
        """Clean up resources"""
        self.logger.info("Cleaning up...")
        self.running.clear()
        
        if self.tft32:
            try:
                self.tft32.disconnect()
            except Exception as e:
                self.logger.error(f"Error during TFT32 cleanup: {e}")
        
        self.logger.info("Cleanup complete")
    
    def run(self):
        """Run the monitor application"""
        try:
            if not self.initialize_components():
                self.logger.error("Failed to initialize, exiting")
                return 1
            
            # Start main loop
            self.main_loop()
            
        except Exception as e:
            self.logger.error(f"Fatal error: {e}")
            return 1
        finally:
            self.cleanup()
        
        return 0

def main():
    """Entry point"""
    monitor = KlipperTFT32Monitor()
    exit_code = monitor.run()
    sys.exit(exit_code)

if __name__ == "__main__":
    main() 