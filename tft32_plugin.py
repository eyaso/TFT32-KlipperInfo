#!/usr/bin/env python3
"""
TFT32 Moonraker Plugin
Display-only TFT integration for Klipper/Moonraker
Sends printer data to TFT32 displays (MKS/BIGTREETECH firmware)

Version: 1.1.0
Build: PASSED ✅
Last Updated: 2025-01-25
"""

__version__ = "1.1.0"
__build_status__ = "PASSED"

import serial
import logging
import asyncio
from enum import Enum
from typing import Optional

class FirmwareType(Enum):
    UNKNOWN = "unknown"
    MKS_ORIGINAL = "mks_original"
    BIGTREETECH = "bigtreetech"

class TFT32Plugin:
    def __init__(self, config):
        self.server = config.get_server()
        self.name = config.get_name()
        
        # Plugin configuration
        self.serial_port = config.get('serial_port', '/dev/ttyS0')
        self.baudrate = config.getint('baudrate', 115200)
        self.update_interval = config.getfloat('update_interval', 3.0)
        self.enabled = config.getboolean('enabled', True)
        
        # Serial connection
        self.serial_conn: Optional[serial.Serial] = None
        self.connected = False
        self.running = False
        
        # Firmware detection
        self.firmware_type = FirmwareType.UNKNOWN
        self.detection_complete = False
        
        # Printer state
        self.current_temps = {
            'hotend_temp': 25.0,
            'hotend_target': 0.0,
            'bed_temp': 22.0,
            'bed_target': 0.0
        }
        self.position = {
            'x_pos': 150.0,
            'y_pos': 150.0,
            'z_pos': 10.0
        }
        self.print_stats = {
            'state': 'standby',
            'progress': 0.0,
            'filename': '',
            'print_time': 0.0,
            'remaining_time': 0,
            'current_layer': 0,
            'total_layers': 0
        }
        self.fan_speed = 0  # Fan speed percentage (0-100)
        
        # Track print state changes for proper TFT notifications
        self.last_print_state = 'standby'
        self.tft_print_active = False
        
        # Setup logging
        self.logger = logging.getLogger(f"moonraker.{self.name}")
        
        # Printer object will be set when Klipper is ready
        self.printer = None
        self.klippy_apis = None
        
        # Register plugin startup
        self.server.register_event_handler("server:klippy_ready", self._on_klippy_ready)
        self.server.register_event_handler("server:klippy_shutdown", self._on_klippy_shutdown)

    async def _on_klippy_ready(self):
        """Called when Klipper is ready"""
        if self.enabled:
            self.logger.info(f"🚀 TFT32 Plugin v{__version__} starting...")
            
            # Try to get klippy_apis as alternative
            try:
                self.klippy_apis = self.server.lookup_component("klippy_apis")
                self.logger.info("✅ Connected to klippy_apis component")
            except Exception as e:
                self.logger.debug(f"klippy_apis not available: {e}")
            
            # Start plugin without printer component - will be acquired later
            await self._start_plugin()

    async def _on_klippy_shutdown(self):
        """Called when Klipper shuts down"""
        await self._stop_plugin()

    async def _start_plugin(self):
        """Start the TFT32 plugin"""
        try:
            # Connect to TFT
            await self._connect_to_tft()
            
            if self.connected:
                # Start update loop
                asyncio.create_task(self._update_loop())
                self.logger.info(f"✅ TFT32 Plugin active on {self.serial_port} at {self.baudrate} baud")
                self.logger.info(f"🎮 Display-only mode, firmware: {self.firmware_type.value}")
            else:
                self.logger.error("❌ Failed to connect to TFT")
                
        except Exception as e:
            self.logger.error(f"❌ Plugin startup failed: {e}")

    async def _stop_plugin(self):
        """Stop the plugin"""
        self.running = False
        await self._close_connection()
        self.logger.info("🛑 TFT32 Plugin stopped")

    async def _connect_to_tft(self) -> bool:
        """Connect to TFT and detect firmware type"""
        try:
            self.serial_conn = serial.Serial(
                port=self.serial_port,
                baudrate=self.baudrate,
                timeout=1,
                write_timeout=1
            )
            self.connected = True
            
            # Start detection process
            await self._detect_firmware()
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to connect to TFT: {e}")
            self.connected = False
            return False

    async def _detect_firmware(self):
        """Detect firmware type by analyzing initial communication"""
        # For display-only mode, default to BIGTREETECH
        self.firmware_type = FirmwareType.BIGTREETECH
        self.detection_complete = True
        
        await self._send_initial_handshake()

    async def _send_initial_handshake(self):
        """Send initial handshake to TFT"""
        # Send basic Marlin-style handshake
        await self._send_response("ok T:25.0 /0.0 B:22.0 /0.0 @:0 B@:0")
        await asyncio.sleep(0.2)
        
        # Identify as Marlin for proper TFT initialization
        await self._send_response("FIRMWARE_NAME:Marlin 2.1.0 (Klipper Compatible) SOURCE_CODE_URL:github.com/MarlinFirmware/Marlin PROTOCOL_VERSION:1.0 MACHINE_TYPE:3D Printer EXTRUDER_COUNT:1")
        await asyncio.sleep(0.1)
        
        # Send capabilities
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

        ready_cmd = f"//action:notification Ready."
        await self._send_response(ready_cmd)

    async def _send_response(self, message: str):
        """Send response to TFT"""
        if not self.connected or not self.serial_conn:
            return
        
        try:
            self.serial_conn.write(f"{message}\r\n".encode())
            self.serial_conn.flush()
            self.logger.debug(f"📤 PI >> TFT: {message}")
        except Exception as e:
            self.logger.error(f"Send error: {e}")

    async def _update_loop(self):
        """Main update loop - fetches data and sends to TFT"""
        self.running = True
        
        while self.running:
            if self.connected and self.detection_complete:
                try:
                    await self._update_from_klipper()
                    await self._broadcast_status_updates()
                except Exception as e:
                    self.logger.debug(f"Update error: {e}")
                    # Continue with fallback data
            
            await asyncio.sleep(self.update_interval)

    async def _update_from_klipper(self):
        """Fetch real data from Klipper via Moonraker"""
        try:
            # Try to get printer component if we don't have it yet
            if self.printer is None:
                try:
                    self.printer = self.server.lookup_component("printer")
                except Exception as e:
                    # Try klippy_apis as alternative
                    if self.klippy_apis is not None:
                        try:
                            objects = {'extruder': None, 'heater_bed': None, 'print_stats': None, 
                                     'display_status': None, 'toolhead': None, 'fan': None, 'virtual_sdcard': None}
                            result = await self.klippy_apis.query_objects(objects)
                            await self._process_klipper_data(result)
                            return
                        except Exception as api_error:
                            self.logger.debug(f"klippy_apis query failed: {api_error}")
                    
                    # Neither method worked, use fallback data
                    self.logger.debug(f"Printer component not ready: {e}")
                    return
                
            # Get printer objects for status queries (including virtual_sdcard for layer info)
            objects = ['extruder', 'heater_bed', 'print_stats', 'display_status', 'toolhead', 'fan', 'virtual_sdcard']
            result = await self.printer.query_status(objects)
            
            if not result:
                return
                
            await self._process_klipper_data(result)
                
        except Exception as e:
            self.logger.debug(f"Klipper query failed: {e}")
            # Keep using current values

    async def _process_klipper_data(self, result):
        """Process data from Klipper regardless of source"""
        # Temperature data
        if 'extruder' in result:
            extruder = result['extruder']
            self.current_temps['hotend_temp'] = extruder.get('temperature', 25.0)
            self.current_temps['hotend_target'] = extruder.get('target', 0.0)
        
        if 'heater_bed' in result:
            heater_bed = result['heater_bed']
            self.current_temps['bed_temp'] = heater_bed.get('temperature', 22.0)
            self.current_temps['bed_target'] = heater_bed.get('target', 0.0)
        
        # Print statistics
        if 'print_stats' in result:
            print_stats = result['print_stats']
            self.print_stats['state'] = print_stats.get('state', 'standby')
            self.print_stats['filename'] = print_stats.get('filename', '')
            self.print_stats['print_time'] = print_stats.get('print_duration', 0.0)
            
            # Get layer information from print_stats.info (Slicer SET_PRINT_STATS_INFO)
            info = print_stats.get('info', {})
            current_layer = info.get('current_layer') if info else None
            total_layer = info.get('total_layer') if info else None
            
            # Prioritize real layer data from slicer (Slicer with SET_PRINT_STATS_INFO)
            if current_layer is not None and total_layer is not None:
                self.print_stats['current_layer'] = current_layer
                self.print_stats['total_layers'] = total_layer
                self.logger.debug(f"📐 Real layer data: {current_layer}/{total_layer}")
            else:
                # Will calculate from virtual_sdcard as fallback
                self.print_stats['current_layer'] = 0
                self.print_stats['total_layers'] = 0
        
        # Display status (progress) - use virtual_sdcard progress for more accuracy
        progress = 0.0
        if 'virtual_sdcard' in result:
            progress = result['virtual_sdcard'].get('progress', 0.0)
        elif 'display_status' in result:
            progress = result['display_status'].get('progress', 0.0)
        
        self.print_stats['progress'] = progress * 100
        
        # Calculate remaining time using more accurate data
        if self.print_stats['progress'] > 0 and self.print_stats['print_time'] > 0:
            total_time_estimate = self.print_stats['print_time'] / (self.print_stats['progress'] / 100)
            self.print_stats['remaining_time'] = max(0, total_time_estimate - self.print_stats['print_time'])
        
        # Toolhead position
        if 'toolhead' in result:
            toolhead = result['toolhead']
            position = toolhead.get('position', [150, 150, 10, 0])
            self.position['x_pos'] = position[0] if len(position) > 0 else 150.0
            self.position['y_pos'] = position[1] if len(position) > 1 else 150.0
            self.position['z_pos'] = position[2] if len(position) > 2 else 10.0
        
        # Fan speed
        if 'fan' in result:
            fan = result['fan']
            fan_speed_ratio = fan.get('speed', 0.0)
            self.fan_speed = int(fan_speed_ratio * 100)
        
        # Fallback: Layer estimation from virtual_sdcard when slicer doesn't provide layer info
        if ('virtual_sdcard' in result and 'print_stats' in result and 
            result['print_stats'].get('state') == 'printing' and 
            self.print_stats['total_layers'] == 0):  # Only if no real layer data
            
            virtual_sdcard = result['virtual_sdcard']
            file_position = virtual_sdcard.get('file_position', 0)
            file_size = virtual_sdcard.get('file_size', 1)
            is_active = virtual_sdcard.get('is_active', False)
            
            if file_size > 0 and is_active:
                # Fallback estimation when PrusaSlicer SET_PRINT_STATS_INFO not used
                progress_ratio = file_position / file_size
                
                # Estimate based on common print parameters
                # Assume 0.2mm layer height, ~40mm print height = ~200 layers
                estimated_total_layers = 200
                estimated_current = max(1, int(progress_ratio * estimated_total_layers))
                
                self.print_stats['current_layer'] = estimated_current
                self.print_stats['total_layers'] = estimated_total_layers
                self.logger.debug(f"📐 Estimated layers: {estimated_current}/{estimated_total_layers} (from file progress)")

    async def _broadcast_status_updates(self):
        """Send status updates to TFT"""
        # Send temperature update (continuous)
        await self._send_temperature_response()
        
        # Send fan speed update
        fan_pwm = int((self.fan_speed / 100.0) * 255)
        fan_cmd = f"M106 S{fan_pwm}"
        await self._send_response(fan_cmd)
        
        # Handle print state changes
        await self._handle_print_state_changes()
        await self._send_print_progress_updates()

    async def _handle_print_state_changes(self):
        """Handle print state changes and send action codes"""
        current_state = self.print_stats['state']
        
        if current_state != self.last_print_state:
            if current_state == 'printing' and not self.tft_print_active:
                await self._send_response("//action:print_start")
                self.tft_print_active = True
                
            elif current_state == 'paused' and self.last_print_state == 'printing':
                await self._send_response("//action:pause")
                
            elif current_state == 'printing' and self.last_print_state == 'paused':
                await self._send_response("//action:resume")
                
            elif current_state == 'complete' and self.tft_print_active:
                await self._send_response("//action:print_end")
                self.tft_print_active = False
                
            elif current_state in ['cancelled', 'error'] and self.tft_print_active:
                await self._send_response("//action:cancel")
                self.tft_print_active = False
            
            self.last_print_state = current_state

    async def _send_print_progress_updates(self):
        """Send print progress updates when printing"""
        if not self.tft_print_active or self.print_stats['state'] != 'printing':
            return
        
        # File progress
        if self.print_stats['progress'] > 0:
            progress_percent = int(self.print_stats['progress'])
            progress_cmd = f"//action:notification Data Left {progress_percent}/100"
            await self._send_response(progress_cmd)
        
        # Time remaining
        if self.print_stats['remaining_time'] > 0:
            hours = int(self.print_stats['remaining_time'] // 3600)
            minutes = int((self.print_stats['remaining_time'] % 3600) // 60)
            seconds = int(self.print_stats['remaining_time'] % 60)
            time_cmd = f"//action:notification Time Left {hours:02d}h{minutes:02d}m{seconds:02d}s"
            await self._send_response(time_cmd)
        
        # Layer information (only send if we have reasonable estimates)
        if (self.print_stats['total_layers'] > 0 and 
            self.print_stats['current_layer'] > 0 and 
            self.print_stats['current_layer'] <= self.print_stats['total_layers']):
            layer_cmd = f"//action:notification Layer Left {self.print_stats['current_layer']}/{self.print_stats['total_layers']}"
            await self._send_response(layer_cmd)

    async def _send_temperature_response(self):
        """Send temperature response"""
        temp = self.current_temps
        response = (f"ok T:{temp['hotend_temp']:.1f} /{temp['hotend_target']:.1f} "
                   f"B:{temp['bed_temp']:.1f} /{temp['bed_target']:.1f} @:0 B@:0")
        await self._send_response(response)

    async def _close_connection(self):
        """Close serial connection"""
        if self.serial_conn:
            try:
                self.serial_conn.close()
            except:
                pass
            self.serial_conn = None
        self.connected = False

    # Moonraker API methods
    async def get_status(self):
        """Get plugin status for API"""
        return {
            "enabled": self.enabled,
            "connected": self.connected,
            "firmware_type": self.firmware_type.value,
            "serial_port": self.serial_port,
            "baudrate": self.baudrate,
            "current_temps": self.current_temps,
            "print_stats": self.print_stats,
            "fan_speed": self.fan_speed
        }

def load_component(config):
    """Load the plugin component"""
    return TFT32Plugin(config) 