#!/usr/bin/env python3
"""
TFT32 Moonraker Plugin
Display-only TFT integration for Klipper/Moonraker
Sends printer data to TFT32 displays (MKS/BIGTREETECH firmware)
"""

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
            'remaining_time': 0
        }
        self.fan_speed = 0  # Fan speed percentage (0-100)
        
        # Track print state changes for proper TFT notifications
        self.last_print_state = 'standby'
        self.tft_print_active = False
        
        # Setup logging
        self.logger = logging.getLogger(f"moonraker.{self.name}")
        
        # Get printer object for status queries
        self.printer = self.server.lookup_component("printer")
        
        # Register plugin startup
        self.server.register_event_handler("server:klippy_ready", self._on_klippy_ready)
        self.server.register_event_handler("server:klippy_shutdown", self._on_klippy_shutdown)

    async def _on_klippy_ready(self):
        """Called when Klipper is ready"""
        if self.enabled:
            self.logger.info("🚀 TFT32 Plugin starting...")
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
        self.logger.info("🔍 Detecting TFT firmware...")
        
        # For display-only mode, default to BIGTREETECH
        self.firmware_type = FirmwareType.BIGTREETECH
        self.detection_complete = True
        self.logger.info(f"🎯 Using firmware type: {self.firmware_type.value}")
        
        await self._send_initial_handshake()

    async def _send_initial_handshake(self):
        """Send initial handshake to TFT"""
        self.logger.info("🤝 Sending TFT handshake...")
        
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

        self.logger.info("✅ TFT handshake complete")

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
            # Get printer status from Klipper
            result = await self.printer.lookup_object("query_status", None)
            if result is None:
                return
                
            # Temperature data
            extruder_status = result.get("extruder", {})
            if extruder_status:
                self.current_temps['hotend_temp'] = extruder_status.get('temperature', 25.0)
                self.current_temps['hotend_target'] = extruder_status.get('target', 0.0)
            
            heater_bed_status = result.get("heater_bed", {})
            if heater_bed_status:
                self.current_temps['bed_temp'] = heater_bed_status.get('temperature', 22.0)
                self.current_temps['bed_target'] = heater_bed_status.get('target', 0.0)
            
            # Print statistics
            print_stats = result.get("print_stats", {})
            if print_stats:
                self.print_stats['state'] = print_stats.get('state', 'standby')
                self.print_stats['filename'] = print_stats.get('filename', '')
                self.print_stats['print_time'] = print_stats.get('print_duration', 0.0)
            
            # Display status (progress)
            display_status = result.get("display_status", {})
            if display_status:
                self.print_stats['progress'] = display_status.get('progress', 0.0) * 100
                
                # Calculate remaining time
                if self.print_stats['progress'] > 0 and self.print_stats['print_time'] > 0:
                    total_time_estimate = self.print_stats['print_time'] / (self.print_stats['progress'] / 100)
                    self.print_stats['remaining_time'] = max(0, total_time_estimate - self.print_stats['print_time'])
            
            # Toolhead position
            toolhead = result.get("toolhead", {})
            if toolhead:
                position = toolhead.get('position', [150, 150, 10, 0])
                self.position['x_pos'] = position[0] if len(position) > 0 else 150.0
                self.position['y_pos'] = position[1] if len(position) > 1 else 150.0
                self.position['z_pos'] = position[2] if len(position) > 2 else 10.0
            
            # Fan speed
            fan = result.get("fan", {})
            if fan:
                fan_speed_ratio = fan.get('speed', 0.0)
                self.fan_speed = int(fan_speed_ratio * 100)
                
        except Exception as e:
            self.logger.debug(f"Klipper query failed: {e}")
            # Keep using current values

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
            self.logger.info(f"🔄 Print state: {self.last_print_state} → {current_state}")
            
            if current_state == 'printing' and not self.tft_print_active:
                await self._send_response("//action:print_start")
                self.tft_print_active = True
                self.logger.info("🚀 Print started on TFT")
                
            elif current_state == 'paused' and self.last_print_state == 'printing':
                await self._send_response("//action:pause")
                self.logger.info("⏸️ Print paused on TFT")
                
            elif current_state == 'printing' and self.last_print_state == 'paused':
                await self._send_response("//action:resume")
                self.logger.info("▶️ Print resumed on TFT")
                
            elif current_state == 'complete' and self.tft_print_active:
                await self._send_response("//action:print_end")
                self.tft_print_active = False
                self.logger.info("✅ Print completed on TFT")
                
            elif current_state in ['cancelled', 'error'] and self.tft_print_active:
                await self._send_response("//action:cancel")
                self.tft_print_active = False
                self.logger.info("❌ Print cancelled on TFT")
            
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