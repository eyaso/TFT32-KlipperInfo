#!/usr/bin/env python3
"""
RRF (RepRap Firmware) Compatible TFT32 Client
Specifically designed for BIGTREETECH firmware configured for RRF
"""

import serial
import time
import logging
import asyncio
import requests
import json
import re
from typing import Optional, Dict, Any

class RRFTFTClient:
    def __init__(self, serial_port: str = '/dev/ttyS0', baudrate: int = 57600):
        self.serial_port = serial_port
        self.baudrate = baudrate
        self.serial_conn: Optional[serial.Serial] = None
        self.connected = False
        self.running = False
        
        # Moonraker settings
        try:
            import config
            self.moonraker_host = getattr(config, 'MOONRAKER_HOST', 'localhost')
            self.moonraker_port = getattr(config, 'MOONRAKER_PORT', 7125)
            self.serial_port = getattr(config, 'TFT32_SERIAL_PORT', '/dev/ttyS0')
            self.baudrate = getattr(config, 'TFT32_BAUDRATE', 57600)
        except ImportError:
            self.moonraker_host = 'localhost'
            self.moonraker_port = 7125
        
        # RRF State tracking
        self.current_temps = {
            'hotend_temp': 25.0,
            'hotend_target': 0.0,
            'bed_temp': 22.0,
            'bed_target': 0.0
        }
        self.print_stats = {
            'state': 'standby',
            'progress': 0.0,
            'filename': '',
            'print_time': 0.0,
            'remaining_time': 0
        }
        self.position = {
            'x_pos': 150.0,
            'y_pos': 150.0,
            'z_pos': 10.0
        }
        self.motion_report = {
            'print_speed': 100,
            'flow_rate': 100,
            'fan_speed': 0
        }
        
        # RRF connection state
        self.first_m105_received = False
        self.connection_established = False
        
        # Setup logging
        self.logger = logging.getLogger('RRFTFTClient')
        self.logger.setLevel(logging.INFO)
        
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    async def connect_and_start(self) -> bool:
        """Connect to TFT and start communication"""
        try:
            self.serial_conn = serial.Serial(
                port=self.serial_port,
                baudrate=self.baudrate,
                timeout=1,
                write_timeout=1
            )
            self.connected = True
            self.logger.info(f"🔌 Connected to {self.serial_port} at {self.baudrate} baud")
            
            # Test Moonraker connection
            await self._test_moonraker_connection()
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Failed to connect: {e}")
            self.connected = False
            return False

    async def _test_moonraker_connection(self):
        """Test connection to Moonraker"""
        try:
            url = f"http://{self.moonraker_host}:{self.moonraker_port}/server/info"
            response = requests.get(url, timeout=3)
            if response.status_code == 200:
                self.logger.info(f"✅ Moonraker connected at {self.moonraker_host}:{self.moonraker_port}")
            else:
                self.logger.warning(f"⚠️ Moonraker returned status {response.status_code}")
        except Exception as e:
            self.logger.warning(f"⚠️ Cannot connect to Moonraker: {e}")
            self.logger.info("📊 Will use fallback data for TFT")

    async def _send_response(self, message: str):
        """Send response to TFT"""
        if not self.connected or not self.serial_conn:
            return
        
        try:
            self.serial_conn.write(f"{message}\r\n".encode())
            self.serial_conn.flush()
            self.logger.info(f"📤 PI >> TFT: {message}")
        except Exception as e:
            self.logger.error(f"Send error: {e}")

    async def communication_loop(self):
        """Main communication loop"""
        self.logger.info("🔄 Starting RRF communication loop")
        self.logger.info("🎯 Waiting for TFT to send M105 command...")
        self.running = True
        
        while self.running:
            if not self.connected:
                await asyncio.sleep(1.0)
                continue
            
            try:
                if self.serial_conn and self.serial_conn.in_waiting > 0:
                    incoming = self.serial_conn.readline().decode('utf-8', errors='ignore').strip()
                    if incoming:
                        await self._handle_command(incoming)
                
                await asyncio.sleep(0.1)
                
            except Exception as e:
                self.logger.error(f"Communication error: {e}")

    async def _handle_command(self, command: str):
        """Handle incoming commands using RRF protocol"""
        self.logger.info(f"📥 TFT >> PI: '{command}'")
        
        # First M105 establishes connection
        if 'M105' in command and not self.first_m105_received:
            self.first_m105_received = True
            self.connection_established = True
            self.logger.info("🤝 First M105 received - connection established!")
            await self._send_rrf_handshake()
        
        # Handle commands
        if 'M105' in command:
            await self._send_rrf_temperature_response()
        elif 'M115' in command:
            await self._send_rrf_firmware_response()
        elif 'M114' in command:
            await self._send_rrf_position_response()
        elif 'M27' in command:
            await self._send_rrf_sd_status_response()
        elif 'M20' in command:
            await self._send_rrf_file_list_response()
        elif 'M92' in command:
            await self._send_rrf_steps_response()
        elif command.startswith('M104') or command.startswith('M109'):
            await self._handle_hotend_temp_command(command)
        elif command.startswith('M140') or command.startswith('M190'):
            await self._handle_bed_temp_command(command)
        elif command.startswith('G28'):
            self.logger.info("🏠 TFT requested home")
            # RRF doesn't need "ok" for G28
        elif 'action:' in command:
            await self._handle_action_command(command)
        else:
            # RRF typically doesn't send "ok" for unknown commands
            pass

    async def _send_rrf_handshake(self):
        """Send RRF-style handshake sequence"""
        self.logger.info("🤝 Sending RRF handshake...")
        
        # RRF handshake sequence
        handshake_sequence = [
            # Firmware identification (RRF style)
            "FIRMWARE_NAME: RepRapFirmware for Generic FIRMWARE_VERSION: 3.4.0 ELECTRONICS: Generic FIRMWARE_DATE: 2023-01-01",
            
            # Capabilities
            "Cap:EEPROM:0",
            "Cap:AUTOREPORT_TEMP:1", 
            "Cap:HOST_ACTION_COMMANDS:1",
            "Cap:PROMPT_SUPPORT:1",
            "Cap:AUTOLEVEL:1",
            "Cap:RUNOUT:0",
            "Cap:Z_PROBE:1",
            "Cap:LEVELING_DATA:1",
            "Cap:BUILD_PERCENT:1",
            "Cap:SOFTWARE_POWER:0",
            "Cap:TOGGLE_LIGHTS:0",
            "Cap:CASE_LIGHT_BRIGHTNESS:0",
            "Cap:EMERGENCY_PARSER:1",
        ]
        
        for response in handshake_sequence:
            await self._send_response(response)
            await asyncio.sleep(0.1)

    async def _send_rrf_temperature_response(self):
        """Send RRF-style temperature response (NO @ symbol)"""
        temp = self.current_temps
        
        # RRF format: T:XX.X /YY.Y B:ZZ.Z /WW.W (NO @ symbol!)
        response = (f"T:{temp['hotend_temp']:.1f} /{temp['hotend_target']:.1f} "
                   f"B:{temp['bed_temp']:.1f} /{temp['bed_target']:.1f}")
        
        await self._send_response(response)

    async def _send_rrf_firmware_response(self):
        """Send RRF firmware identification"""
        await self._send_response("FIRMWARE_NAME: RepRapFirmware for Generic FIRMWARE_VERSION: 3.4.0")

    async def _send_rrf_position_response(self):
        """Send RRF position response"""
        pos = self.position
        response = f"X:{pos['x_pos']:.2f} Y:{pos['y_pos']:.2f} Z:{pos['z_pos']:.2f} E:0.00"
        await self._send_response(response)

    async def _send_rrf_sd_status_response(self):
        """Send RRF SD card status"""
        if self.print_stats['state'] == 'printing':
            response = f"SD printing byte {int(self.print_stats['progress']*10)}/1000"
        else:
            response = "Not SD printing"
        await self._send_response(response)

    async def _send_rrf_file_list_response(self):
        """Send RRF file list"""
        await self._send_response("Begin file list")
        if self.print_stats['filename']:
            await self._send_response(self.print_stats['filename'])
        else:
            await self._send_response("test.gcode")
        await self._send_response("End file list")

    async def _send_rrf_steps_response(self):
        """Send RRF steps per mm response"""
        await self._send_response("M92 X80.00 Y80.00 Z400.00 E420.00")

    async def _handle_hotend_temp_command(self, command: str):
        """Handle hotend temperature setting"""
        temp_match = re.search(r'S(\d+)', command)
        if temp_match:
            target_temp = float(temp_match.group(1))
            self.logger.info(f"🔥 TFT set hotend target: {target_temp}°C")
            # TODO: Send to Klipper via Moonraker

    async def _handle_bed_temp_command(self, command: str):
        """Handle bed temperature setting"""
        temp_match = re.search(r'S(\d+)', command)
        if temp_match:
            target_temp = float(temp_match.group(1))
            self.logger.info(f"🛏️ TFT set bed target: {target_temp}°C")
            # TODO: Send to Klipper via Moonraker

    async def _handle_action_command(self, command: str):
        """Handle action commands from TFT"""
        if "remote pause" in command:
            self.logger.info("🎮 TFT requested pause")
            await self._send_moonraker_command("printer/print/pause")
        elif "remote resume" in command:
            self.logger.info("🎮 TFT requested resume")
            await self._send_moonraker_command("printer/print/resume")
        elif "remote cancel" in command:
            self.logger.info("🎮 TFT requested cancel")
            await self._send_moonraker_command("printer/print/cancel")

    async def _send_moonraker_command(self, endpoint: str):
        """Send command to Moonraker"""
        try:
            url = f"http://{self.moonraker_host}:{self.moonraker_port}/{endpoint}"
            response = requests.post(url, timeout=5)
            if response.status_code == 200:
                self.logger.info(f"✅ Moonraker command sent: {endpoint}")
            else:
                self.logger.error(f"❌ Moonraker command failed: {response.status_code}")
        except Exception as e:
            self.logger.error(f"❌ Failed to send Moonraker command: {e}")

    async def update_loop(self):
        """Update printer data from Moonraker"""
        while self.running:
            if self.connected and self.connection_established:
                try:
                    await self._update_from_moonraker()
                    await self._send_comprehensive_data()
                except Exception as e:
                    self.logger.error(f"Update error: {e}")
            
            await asyncio.sleep(3.0)  # Update every 3 seconds

    async def _update_from_moonraker(self):
        """Fetch real data from Moonraker"""
        try:
            # Get temperature data
            temp_url = f"http://{self.moonraker_host}:{self.moonraker_port}/printer/objects/query?heater_bed&extruder"
            response = requests.get(temp_url, timeout=3)
            
            if response.status_code == 200:
                data = response.json()
                status = data.get('result', {}).get('status', {})
                
                if 'extruder' in status:
                    self.current_temps['hotend_temp'] = status['extruder'].get('temperature', 0.0)
                    self.current_temps['hotend_target'] = status['extruder'].get('target', 0.0)
                
                if 'heater_bed' in status:
                    self.current_temps['bed_temp'] = status['heater_bed'].get('temperature', 0.0)
                    self.current_temps['bed_target'] = status['heater_bed'].get('target', 0.0)
            
            # Get print stats and position
            stats_url = f"http://{self.moonraker_host}:{self.moonraker_port}/printer/objects/query?print_stats&display_status&toolhead"
            response = requests.get(stats_url, timeout=3)
            
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
                
                if 'toolhead' in status:
                    toolhead = status['toolhead']
                    position = toolhead.get('position', [0, 0, 0, 0])
                    self.position['x_pos'] = position[0] if len(position) > 0 else 0.0
                    self.position['y_pos'] = position[1] if len(position) > 1 else 0.0
                    self.position['z_pos'] = position[2] if len(position) > 2 else 0.0
            
        except Exception as e:
            self.logger.debug(f"Moonraker update failed (using fallback data): {e}")

    async def _send_comprehensive_data(self):
        """Send comprehensive KLIP data for custom screen"""
        # Format time
        elapsed_hours = int(self.print_stats['print_time'] // 3600)
        elapsed_mins = int((self.print_stats['print_time'] % 3600) // 60)
        elapsed_time = f"{elapsed_hours:02d}:{elapsed_mins:02d}"
        
        remaining_hours = int(self.print_stats['remaining_time'] // 3600)
        remaining_mins = int((self.print_stats['remaining_time'] % 3600) // 60)
        remaining_time = f"{remaining_hours:02d}:{remaining_mins:02d}"
        
        # Clean filename
        filename = self.print_stats['filename'] or 'No file'
        if '/' in filename:
            filename = filename.split('/')[-1]
        if len(filename) > 20:
            filename = filename[:17] + "..."
        
        # Create KLIP string for custom screen
        comprehensive_string = (
            f"KLIP:"
            f"{self.current_temps['hotend_temp']:.1f}:"
            f"{self.current_temps['hotend_target']:.1f}:"
            f"{self.current_temps['bed_temp']:.1f}:"
            f"{self.current_temps['bed_target']:.1f}:"
            f"{self.print_stats['state']}:"
            f"{self.print_stats['progress']:.0f}:"
            f"{self.position['x_pos']:.2f}:"
            f"{self.position['y_pos']:.2f}:"
            f"{self.position['z_pos']:.2f}:"
            f"{elapsed_time}/{remaining_time}:"
            f"{filename}:"
            f"{self.motion_report['print_speed']}:"
            f"{self.motion_report['flow_rate']}:"
            f"{self.motion_report['fan_speed']}"
        )
        
        await self._send_response(comprehensive_string)
        self.logger.debug("📤 Sent KLIP comprehensive data")

    async def close(self):
        """Clean shutdown"""
        self.logger.info("🛑 Shutting down")
        self.running = False
        
        if self.serial_conn:
            try:
                self.serial_conn.close()
            except:
                pass
            self.serial_conn = None
        
        self.connected = False

async def main():
    """Main function"""
    try:
        import config
        serial_port = getattr(config, 'TFT32_SERIAL_PORT', '/dev/ttyS0')
        baudrate = getattr(config, 'TFT32_BAUDRATE', 57600)
    except ImportError:
        serial_port = '/dev/ttyS0'
        baudrate = 57600
    
    print("🚀 RRF TFT32 Client for BIGTREETECH")
    print("=" * 50)
    print(f"📡 Port: {serial_port} at {baudrate} baud")
    print("🔧 Configured for RepRap Firmware (RRF) mode")
    print("🌙 Connects to Moonraker for real printer data")
    print("⚠️  NO @ symbol in temperature responses (RRF)")
    print()
    
    client = RRFTFTClient(serial_port, baudrate)
    
    try:
        if await client.connect_and_start():
            print("✅ Connected! Waiting for TFT to send M105...")
            print("📊 Will fetch real data from Moonraker")
            print("🎮 TFT controls will work (pause, resume, cancel)")
            print("💡 Press Ctrl+C to stop")
            print()
            
            await asyncio.gather(
                client.communication_loop(),
                client.update_loop()
            )
        else:
            print("❌ Failed to connect to TFT")
            return 1
            
    except KeyboardInterrupt:
        print("\n🛑 Stopping...")
    finally:
        await client.close()
    
    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main()) 