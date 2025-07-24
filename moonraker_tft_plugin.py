#!/usr/bin/env python3
"""
Moonraker TFT32 Plugin
A Moonraker-compatible plugin for BIGTREETECH TFT32 displays
Based on OctoPrint BTT Touch Support protocol
"""

import asyncio
import logging
import serial
import time
import json
from typing import Dict, Any, Optional

# Moonraker imports (comment out if running standalone)
try:
    from moonraker.components.http_client import HttpClient
    from moonraker.confighelper import ConfigHelper
    MOONRAKER_AVAILABLE = True
except ImportError:
    MOONRAKER_AVAILABLE = False
    # Fallback for standalone mode
    import requests

class TFT32Plugin:
    def __init__(self, config: Optional[Any] = None):
        """Initialize TFT32 plugin"""
        self.name = "tft32_display"
        self.logger = logging.getLogger(f"moonraker.{self.name}")
        
        # Configuration
        if config and MOONRAKER_AVAILABLE:
            # Moonraker mode
            self.serial_port = config.get('serial_port', '/dev/ttyS0')
            self.baudrate = config.getint('baudrate', 250000)
            self.moonraker_host = config.get('moonraker_host', 'localhost')
            self.moonraker_port = config.getint('moonraker_port', 7125)
            self.update_interval = config.getfloat('update_interval', 2.0)
        else:
            # Standalone mode - load from config file
            try:
                import config
                self.serial_port = getattr(config, 'TFT32_SERIAL_PORT', '/dev/ttyS0')
                self.baudrate = getattr(config, 'TFT32_BAUDRATE', 250000)
                self.moonraker_host = getattr(config, 'MOONRAKER_HOST', 'localhost')
                self.moonraker_port = getattr(config, 'MOONRAKER_PORT', 7125)
                self.update_interval = 2.0
            except ImportError:
                # Default values
                self.serial_port = '/dev/ttyS0'
                self.baudrate = 250000
                self.moonraker_host = 'localhost'
                self.moonraker_port = 7125
                self.update_interval = 2.0
        
        # State
        self.serial_conn: Optional[serial.Serial] = None
        self.connected = False
        self.running = False
        self.serial_port_nr = 0  # TFT serial port number (for M118 commands)
        
        # Printer state
        self.current_temps = {
            'hotend_temp': 0.0,
            'hotend_target': 0.0,
            'bed_temp': 0.0,
            'bed_target': 0.0
        }
        self.print_stats = {
            'state': 'standby',
            'progress': 0.0,
            'filename': '',
            'print_time': 0.0,
            'remaining_time': 0
        }
        
        self.logger.info(f"TFT32 Plugin initialized - Port: {self.serial_port}, Baud: {self.baudrate}")

    async def component_init(self):
        """Initialize component (Moonraker compatibility)"""
        await self.connect_serial()
        if self.connected:
            asyncio.create_task(self.communication_loop())
            asyncio.create_task(self.update_loop())

    async def connect_serial(self) -> bool:
        """Connect to TFT32 via serial"""
        try:
            self.serial_conn = serial.Serial(
                port=self.serial_port,
                baudrate=self.baudrate,
                timeout=1,
                write_timeout=1
            )
            self.connected = True
            self.logger.info(f"Connected to TFT32 on {self.serial_port} at {self.baudrate} baud")
            
            # Send initial handshake
            await self._send_initial_handshake()
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to connect to TFT32: {e}")
            self.connected = False
            return False

    async def _send_initial_handshake(self):
        """Send initial handshake sequence"""
        self.logger.info("Sending initial handshake to TFT32...")
        
        # Initial temperature response
        await self._send_response("ok T:25.0 /0.0 B:22.0 /0.0 @:0 B@:0")
        await asyncio.sleep(0.2)
        
        # Firmware identification with action command support
        await self._send_response("FIRMWARE_NAME:Klipper HOST_ACTION_COMMANDS:1 EXTRUDER_COUNT:1")
        await asyncio.sleep(0.1)
        
        # Capabilities
        capabilities = [
            "Cap:EEPROM:1",
            "Cap:AUTOREPORT_TEMP:1",
            "Cap:HOST_ACTION_COMMANDS:1",
            "Cap:PROMPT_SUPPORT:1",
        ]
        
        for cap in capabilities:
            await self._send_response(cap)
            await asyncio.sleep(0.05)
        
        await self._send_response("ok")
        self.logger.info("Initial handshake completed")

    async def _send_response(self, message: str):
        """Send response to TFT32"""
        if not self.connected or not self.serial_conn:
            return
        
        try:
            self.serial_conn.write(f"{message}\r\n".encode())
            self.serial_conn.flush()
            self.logger.debug(f"📤 PI >> TFT: {message}")
        except Exception as e:
            self.logger.error(f"Failed to send response: {e}")
            await self._handle_serial_error()

    async def _handle_serial_error(self):
        """Handle serial communication errors"""
        self.logger.warning("Serial error detected, attempting reconnection...")
        self.connected = False
        if self.serial_conn:
            try:
                self.serial_conn.close()
            except:
                pass
            self.serial_conn = None
        
        # Attempt reconnection after delay
        await asyncio.sleep(2.0)
        await self.connect_serial()

    async def communication_loop(self):
        """Main communication loop - handle incoming TFT commands"""
        self.logger.info("Starting TFT32 communication loop")
        self.running = True
        
        while self.running:
            if not self.connected:
                await asyncio.sleep(1.0)
                continue
                
            try:
                # Check for incoming data
                if self.serial_conn and self.serial_conn.in_waiting > 0:
                    incoming = self.serial_conn.readline().decode('utf-8', errors='ignore').strip()
                    if incoming:
                        await self._handle_tft_command(incoming)
                
                await asyncio.sleep(0.1)
                
            except Exception as e:
                self.logger.error(f"Communication loop error: {e}")
                await self._handle_serial_error()

    async def _handle_tft_command(self, command: str):
        """Handle commands received from TFT"""
        self.logger.debug(f"📥 TFT >> PI: '{command}'")
        
        try:
            if command.startswith('M105'):  # Temperature request
                await self._send_temperature_response()
            elif command.startswith('M115'):  # Firmware info
                await self._send_firmware_response()
            elif command.startswith('M114'):  # Position request
                await self._send_position_response()
            elif command.startswith('M92'):   # Steps per mm
                await self._send_response("M92 X80.00 Y80.00 Z400.00 E420.00")
                await self._send_response("ok")
            elif 'action:' in command:  # Action commands from TFT
                await self._handle_action_command(command)
            else:
                # Standard OK response for unknown commands
                await self._send_response("ok")
                
        except Exception as e:
            self.logger.error(f"Error handling TFT command '{command}': {e}")

    async def _send_temperature_response(self):
        """Send current temperature data to TFT"""
        response = (f"ok T:{self.current_temps['hotend_temp']:.1f} /"
                   f"{self.current_temps['hotend_target']:.1f} "
                   f"B:{self.current_temps['bed_temp']:.1f} /"
                   f"{self.current_temps['bed_target']:.1f} @:0 B@:0")
        await self._send_response(response)

    async def _send_firmware_response(self):
        """Send firmware identification"""
        await self._send_response("FIRMWARE_NAME:Klipper HOST_ACTION_COMMANDS:1 EXTRUDER_COUNT:1")
        await self._send_response("ok")

    async def _send_position_response(self):
        """Send position data"""
        await self._send_response("X:150.00 Y:150.00 Z:10.00 E:0.00 Count X:12000 Y:12000 Z:4000")
        await self._send_response("ok")

    async def _handle_action_command(self, command: str):
        """Handle action commands from TFT (pause, resume, cancel)"""
        if "remote pause" in command:
            self.logger.info("TFT requested pause")
            await self._send_moonraker_command("printer/print/pause")
        elif "remote resume" in command:
            self.logger.info("TFT requested resume")
            await self._send_moonraker_command("printer/print/resume")
        elif "remote cancel" in command:
            self.logger.info("TFT requested cancel")
            await self._send_moonraker_command("printer/print/cancel")

    async def update_loop(self):
        """Update loop - fetch data from Moonraker and send notifications"""
        self.logger.info("Starting Moonraker update loop")
        
        while self.running:
            if self.connected:
                try:
                    await self._update_printer_data()
                    await self._send_status_notifications()
                except Exception as e:
                    self.logger.error(f"Update loop error: {e}")
            
            await asyncio.sleep(self.update_interval)

    async def _update_printer_data(self):
        """Fetch current printer data from Moonraker"""
        try:
            # Fetch temperature data
            temp_url = f"http://{self.moonraker_host}:{self.moonraker_port}/printer/objects/query?heater_bed&extruder"
            
            if MOONRAKER_AVAILABLE:
                # Use Moonraker's HTTP client if available
                # This would need to be implemented based on Moonraker's API
                pass
            else:
                # Standalone mode - use requests
                response = requests.get(temp_url, timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    status = data.get('result', {}).get('status', {})
                    
                    # Update temperatures
                    if 'extruder' in status:
                        self.current_temps['hotend_temp'] = status['extruder'].get('temperature', 0.0)
                        self.current_temps['hotend_target'] = status['extruder'].get('target', 0.0)
                    
                    if 'heater_bed' in status:
                        self.current_temps['bed_temp'] = status['heater_bed'].get('temperature', 0.0)
                        self.current_temps['bed_target'] = status['heater_bed'].get('target', 0.0)
            
            # Fetch print stats
            stats_url = f"http://{self.moonraker_host}:{self.moonraker_port}/printer/objects/query?print_stats&display_status"
            
            if not MOONRAKER_AVAILABLE:
                response = requests.get(stats_url, timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    status = data.get('result', {}).get('status', {})
                    
                    if 'print_stats' in status:
                        stats = status['print_stats']
                        self.print_stats['state'] = stats.get('state', 'standby')
                        self.print_stats['filename'] = stats.get('filename', '')
                        self.print_stats['print_time'] = stats.get('print_duration', 0.0)
                    
                    if 'display_status' in status:
                        display = status['display_status']
                        self.print_stats['progress'] = display.get('progress', 0.0) * 100
                        
        except Exception as e:
            self.logger.error(f"Failed to update printer data: {e}")

    async def _send_status_notifications(self):
        """Send OctoPrint-style status notifications to TFT"""
        if not self.connected:
            return
        
        # Format time remaining
        remaining_hours = int(self.print_stats['remaining_time'] // 3600)
        remaining_minutes = int((self.print_stats['remaining_time'] % 3600) // 60)
        remaining_seconds = int(self.print_stats['remaining_time'] % 60)
        
        # Send time notification
        time_cmd = f"M118 P{self.serial_port_nr} A1 action:notification Time Left {remaining_hours:02d}h{remaining_minutes:02d}m{remaining_seconds:02d}s"
        await self._send_response(time_cmd)
        
        # Send progress notification
        progress_cmd = f"M118 P{self.serial_port_nr} A1 action:notification Data Left {self.print_stats['progress']:.0f}/100"
        await self._send_response(progress_cmd)

    async def _send_moonraker_command(self, endpoint: str):
        """Send command to Moonraker"""
        try:
            url = f"http://{self.moonraker_host}:{self.moonraker_port}/{endpoint}"
            
            if not MOONRAKER_AVAILABLE:
                response = requests.post(url, timeout=5)
                if response.status_code == 200:
                    self.logger.info(f"Moonraker command sent: {endpoint}")
                else:
                    self.logger.error(f"Moonraker command failed: {response.status_code}")
        except Exception as e:
            self.logger.error(f"Failed to send Moonraker command: {e}")

    async def close(self):
        """Clean shutdown"""
        self.logger.info("Shutting down TFT32 plugin")
        self.running = False
        
        if self.serial_conn:
            try:
                self.serial_conn.close()
            except:
                pass
            self.serial_conn = None
        
        self.connected = False

# Moonraker plugin interface
def load_component(config):
    """Load component for Moonraker"""
    return TFT32Plugin(config)

# Standalone mode
async def main():
    """Run in standalone mode for testing"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    plugin = TFT32Plugin()
    
    try:
        await plugin.component_init()
        
        # Keep running until interrupted
        while True:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        print("\n🛑 Shutting down...")
    finally:
        await plugin.close()

if __name__ == "__main__":
    asyncio.run(main()) 