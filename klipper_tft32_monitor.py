#!/usr/bin/env python3
"""
Klipper TFT32 Standard Monitor
Uses built-in BIGTREETECH firmware G-code protocol for maximum compatibility
"""

import time
import logging
import signal
import sys
from typing import Optional
import config
from moonraker_client import MoonrakerClient
from tft32_gcode_client import TFT32StandardClient

class KlipperTFT32StandardMonitor:
    """Main monitor that coordinates Moonraker data with TFT32 using standard G-codes"""
    
    def __init__(self):
        # Setup logging
        logging.basicConfig(
            level=getattr(logging, config.LOG_LEVEL.upper()),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(config.LOG_FILE),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
        # Components
        self.moonraker: Optional[MoonrakerClient] = None
        self.tft32: Optional[TFT32StandardClient] = None
        self.running = False
        
        # Status tracking
        self.connection_status = False
        self.last_temperatures = {}
        self.last_print_stats = {}
        self.last_position = {}
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        self.logger.info(f"Received signal {signum}, shutting down...")
        self.shutdown()
        sys.exit(0)
    
    def initialize(self) -> bool:
        """Initialize all components"""
        try:
            # Initialize Moonraker client
            self.logger.info(f"Connecting to Moonraker at {config.MOONRAKER_HOST}:{config.MOONRAKER_PORT}")
            self.moonraker = MoonrakerClient(
                host=config.MOONRAKER_HOST,
                port=config.MOONRAKER_PORT
            )
            
            if not self.moonraker.connect():
                raise ConnectionError("Cannot connect to Moonraker")
            
            self.logger.info("Moonraker connection established")
            
            # Initialize TFT32 standard G-code client
            self.logger.info(f"Connecting to TFT32 on {config.TFT32_SERIAL_PORT}")
            self.tft32 = TFT32StandardClient(
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
        """Update printer data from Moonraker and send to TFT32 using standard G-codes"""
        try:
            # Check connection
            self.connection_status = self.moonraker.is_connected()
            
            if self.connection_status:
                # Get temperatures
                temps = self.moonraker.get_temperatures()
                if temps:
                    self.last_temperatures = temps
                    # Send to TFT32 using standard format
                    if self.tft32 and self.tft32.is_connected():
                        self.tft32.update_temperatures(temps)
                
                # Get print stats
                stats = self.moonraker.get_print_stats()
                if stats:
                    self.last_print_stats = stats
                    # Convert to standard format and send to TFT32
                    if self.tft32 and self.tft32.is_connected():
                        standard_status = self._convert_print_stats(stats)
                        self.tft32.update_print_status(standard_status)
                
                # Get position data
                position = self.moonraker.get_position()
                if position:
                    self.last_position = position
                    # Position is handled automatically by M114 requests from TFT
                
            else:
                self.logger.warning("Moonraker connection lost, attempting to reconnect...")
                self.moonraker.connect()
                
        except Exception as e:
            self.logger.error(f"Error updating data: {e}")
    
    def _convert_print_stats(self, moonraker_stats: dict) -> dict:
        """Convert Moonraker print stats to standard format for TFT32"""
        # Map Moonraker states to standard states
        state_mapping = {
            'standby': 'standby',
            'printing': 'printing', 
            'paused': 'paused',
            'complete': 'standby',
            'cancelled': 'cancelled',
            'error': 'standby'
        }
        
        moonraker_state = moonraker_stats.get('state', 'standby')
        standard_state = state_mapping.get(moonraker_state, 'standby')
        
        # Calculate progress percentage
        progress = 0.0
        if 'print_stats' in moonraker_stats:
            stats = moonraker_stats['print_stats']
            total_duration = stats.get('total_duration', 0)
            print_duration = stats.get('print_duration', 0)
            if total_duration > 0:
                progress = (print_duration / total_duration) * 100
        
        # Extract filename
        filename = moonraker_stats.get('filename', '')
        if filename.startswith('gcodes/'):
            filename = filename[7:]  # Remove 'gcodes/' prefix
        
        # Calculate remaining time
        remaining_time = 0
        if 'print_stats' in moonraker_stats:
            stats = moonraker_stats['print_stats']
            total_duration = stats.get('total_duration', 0)
            print_duration = stats.get('print_duration', 0)
            if total_duration > print_duration:
                remaining_time = int(total_duration - print_duration)
        
        # Get layer information if available
        current_layer = moonraker_stats.get('current_layer', 0)
        total_layers = moonraker_stats.get('total_layers', 0)
        
        return {
            'state': standard_state,
            'progress': progress,
            'filename': filename,
            'print_time': moonraker_stats.get('print_duration', 0),
            'remaining_time': remaining_time,
            'current_layer': current_layer,
            'total_layers': total_layers
        }
    
    def run(self):
        """Main monitoring loop"""
        if not self.initialize():
            self.logger.error("Failed to initialize, exiting")
            return
        
        self.running = True
        self.logger.info("Starting main monitoring loop")
        
        try:
            while self.running:
                self.update_data()
                time.sleep(config.UPDATE_INTERVAL)
                
        except KeyboardInterrupt:
            self.logger.info("Interrupted by user")
        except Exception as e:
            self.logger.error(f"Unexpected error in main loop: {e}")
        finally:
            self.shutdown()
    
    def shutdown(self):
        """Clean shutdown"""
        self.logger.info("Cleaning up...")
        self.running = False
        
        if self.tft32:
            try:
                self.tft32.disconnect()
            except Exception as e:
                self.logger.error(f"Error disconnecting TFT32: {e}")
        
        if self.moonraker:
            try:
                self.moonraker.disconnect()
            except Exception as e:
                self.logger.error(f"Error disconnecting Moonraker: {e}")
        
        self.logger.info("Cleanup complete")

def main():
    """Main entry point"""
    monitor = KlipperTFT32StandardMonitor()
    monitor.run()

if __name__ == "__main__":
    main() 