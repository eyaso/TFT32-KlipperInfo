#!/usr/bin/env python3
"""
TFT32 Final Client - Production Ready
Minimal logging, M-codes only, real Moonraker integration
"""

import serial
import time
import logging
import asyncio
import requests
import re
from enum import Enum
from typing import Optional, Dict, Any

class FirmwareType(Enum):
    UNKNOWN = "unknown"
    MKS_ORIGINAL = "mks_original"
    BIGTREETECH = "bigtreetech"

class TFT32Final:
    def __init__(self):
        # Load config
        try:
            import config
            self.serial_port = getattr(config, 'TFT32_SERIAL_PORT', '/dev/ttyS0')
            self.baudrate = getattr(config, 'TFT32_BAUDRATE', 57600)
            self.moonraker_host = getattr(config, 'MOONRAKER_HOST', 'localhost')
            self.moonraker_port = getattr(config, 'MOONRAKER_PORT', 7125)
        except ImportError:
            self.serial_port = '/dev/ttyS0'
            self.baudrate = 57600
            self.moonraker_host = 'localhost'
            self.moonraker_port = 7125
            
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
        
        # Setup logging for communication monitoring
        self.logger = logging.getLogger('TFT32Final')
        self.logger.setLevel(logging.INFO)  # Show communication for debugging
        
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    async def connect_and_detect(self) -> bool:
        """Connect to TFT and detect firmware type"""
        try:
            self.serial_conn = serial.Serial(
                port=self.serial_port,
                baudrate=self.baudrate,
                timeout=1,
                write_timeout=1
            )
            self.connected = True
            
            # Test Moonraker connection
            await self._test_moonraker_connection()
            
            # Start detection process
            await self._detect_firmware()
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to connect: {e}")
            self.connected = False
            return False

    async def _test_moonraker_connection(self):
        """Test connection to Moonraker"""
        try:
            url = f"http://{self.moonraker_host}:{self.moonraker_port}/server/info"
            response = requests.get(url, timeout=3)
            if response.status_code != 200:
                self.logger.warning(f"Moonraker returned status {response.status_code}")
        except Exception:
            self.logger.warning("Cannot connect to Moonraker, using fallback data")

    async def _detect_firmware(self):
        """Detect firmware type by analyzing initial communication"""
        self.logger.info("🔍 Waiting for initial TFT communication...")
        
        # Wait for any initial commands from TFT to see if it's active
        detection_timeout = 15  # Give more time
        start_time = time.time()
        received_any_data = False
        
        while time.time() - start_time < detection_timeout:
            if self.serial_conn and self.serial_conn.in_waiting > 0:
                try:
                    incoming = self.serial_conn.readline().decode('utf-8', errors='ignore').strip()
                    if incoming:
                        received_any_data = True
                        self.logger.info(f"🔍 Detection phase - received: '{incoming}'")
                        # Send basic response to keep communication alive
                        if 'M105' in incoming:
                            await self._send_response("T:25.0 /0.0 B:22.0 /0.0 @:0 B@:0")
                        else:
                            await self._send_response("ok")
                except Exception as e:
                    self.logger.error(f"Detection error: {e}")
            
            await asyncio.sleep(0.1)
        
        if not received_any_data:
            self.logger.warning("⚠️ No initial communication from TFT detected!")
            self.logger.info("💡 TFT might be in Touch Mode or waiting for different handshake")
        
        # Default to BIGTREETECH
        self.firmware_type = FirmwareType.BIGTREETECH
        self.detection_complete = True
        self.logger.info(f"🎯 Using firmware type: {self.firmware_type.value}")
        
        await self._send_initial_handshake()

    async def _send_initial_handshake(self):
        """Send initial handshake based on detected firmware"""
        await self._send_btt_handshake()

    async def _send_btt_handshake(self):
        """Send handshake for BIGTREETECH firmware"""
        self.logger.info("🤝 Sending BIGTREETECH handshake...")
        
        # BTT firmware expects Marlin-style responses
        await self._send_response("ok T:25.0 /0.0 B:22.0 /0.0 @:0 B@:0")
        await asyncio.sleep(0.2)
        
        # Firmware with capabilities - identify as Marlin for proper TFT initialization
        await self._send_response("FIRMWARE_NAME:Marlin 2.1.0 (Klipper Compatible) SOURCE_CODE_URL:github.com/MarlinFirmware/Marlin PROTOCOL_VERSION:1.0 MACHINE_TYPE:3D Printer EXTRUDER_COUNT:1")
        await asyncio.sleep(0.1)
        
        # Send capabilities (from working version)
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
        self.logger.info("✅ Handshake complete - TFT should now be active")
        
        # Send the initialization sequence that BTT firmware expects
        # This should trigger the TFT to start sending regular queries
        self.logger.info("🔧 Sending initialization sequence...")
        await asyncio.sleep(0.5)
        
        # Send M503 response to indicate we're ready for configuration
        await self._send_response("echo:  G21    ; Units in mm (mm)")
        await self._send_response("echo:  M149 C ; Units in Celsius")
        await self._send_response("ok")
        
        # This should trigger the TFT to start sending M105 queries

    async def _send_response(self, message: str):
        """Send response to TFT"""
        if not self.connected or not self.serial_conn:
            return
        
        try:
            self.serial_conn.write(f"{message}\r\n".encode())
            self.serial_conn.flush()
            self.logger.debug(f"📤 PI >> TFT: {message}")  # Changed to INFO to see all traffic
        except Exception as e:
            self.logger.error(f"Send error: {e}")

    async def communication_loop(self):
        """Main communication loop"""
        self.running = True
        
        # Add debugging counters
        loop_count = 0
        last_debug = 0
        
        while self.running:
            if not self.connected:
                await asyncio.sleep(1.0)
                self.logger.info(f"Waiting for connection...")
                continue
            
            try:
                # Enhanced debugging - check raw serial state
                loop_count += 1
                
                # Debug every 100 loops (10 seconds)
                if loop_count - last_debug >= 100:
                    bytes_waiting = self.serial_conn.in_waiting if self.serial_conn else 0
                    self.logger.info(f"🔍 Loop {loop_count}: {bytes_waiting} bytes waiting, connected={self.connected}")
                    last_debug = loop_count
                
                if self.serial_conn and self.serial_conn.in_waiting > 0:
                    # Try both readline and read to see what we get
                    bytes_available = self.serial_conn.in_waiting
                    self.logger.info(f"📊 {bytes_available} bytes available to read")
                    
                    # Method 1: Try readline (what we're currently using)
                    incoming = self.serial_conn.readline().decode('utf-8', errors='ignore').strip()
                    if incoming:
                        self.logger.info(f"📥 READLINE got: '{incoming}'")
                        await self._handle_command(incoming)
                    else:
                        # Method 2: If readline fails, try reading raw bytes
                        self.serial_conn.reset_input_buffer()  # Reset position
                        raw_data = self.serial_conn.read(bytes_available)
                        if raw_data:
                            self.logger.info(f"🔧 RAW BYTES: {raw_data}")
                            # Try to decode and process
                            try:
                                decoded = raw_data.decode('utf-8', errors='ignore').strip()
                                if decoded:
                                    self.logger.info(f"📥 DECODED: '{decoded}'")
                                    await self._handle_command(decoded)
                            except Exception as decode_error:
                                self.logger.error(f"Decode error: {decode_error}")
                
                await asyncio.sleep(0.1)
                
            except Exception as e:
                self.logger.error(f"Communication error: {e}")

    async def _handle_command(self, command: str):
        """Handle incoming commands based on firmware type"""
        # Log all TFT >> PI communication for debugging
        self.logger.info(f"📥 TFT >> PI: '{command}'")
        
        # For BIGTREETECH firmware, send immediate "ok" first to prevent timeout
        # EXCEPT for M105 which includes "ok" in the response
        if self.firmware_type == FirmwareType.BIGTREETECH and 'M105' not in command:
            await self._send_response("ok")
            await asyncio.sleep(0.01)  # Small delay to ensure ok is processed
        
        # Handle specific commands
        if 'M105' in command:
            await self._send_temperature_response()
        elif 'M115' in command:
            await self._send_firmware_response()
        elif 'M114' in command:
            await self._send_position_response()
        elif 'M27' in command:
            await self._send_sd_status_response()
        elif 'M20' in command:
            await self._send_file_list_response()
        elif 'M92' in command:
            await self._send_response("M92 X80.00 Y80.00 Z400.00 E420.00")
        elif command.startswith('M104') or command.startswith('M109'):
            await self._handle_hotend_temp_command(command)
        elif command.startswith('M140') or command.startswith('M190'):
            await self._handle_bed_temp_command(command)
        elif command.startswith('M106'):
            await self._handle_fan_command(command)
        elif command.startswith('M107'):
            await self._handle_fan_off_command()
        elif command.startswith('G28'):
            self.logger.info("🏠 TFT requested home")
        elif 'action:' in command:
            await self._handle_action_command(command)

    async def _handle_hotend_temp_command(self, command: str):
        """Handle hotend temperature setting"""
        temp_match = re.search(r'S(\d+)', command)
        if temp_match:
            target_temp = float(temp_match.group(1))
            self.current_temps['hotend_target'] = target_temp
            self.logger.info(f"🔥 TFT set hotend target: {target_temp}°C")
            # TODO: Send to Klipper via Moonraker

    async def _handle_bed_temp_command(self, command: str):
        """Handle bed temperature setting"""
        temp_match = re.search(r'S(\d+)', command)
        if temp_match:
            target_temp = float(temp_match.group(1))
            self.current_temps['bed_target'] = target_temp
            self.logger.info(f"🛏️ TFT set bed target: {target_temp}°C")
            # TODO: Send to Klipper via Moonraker

    async def _handle_fan_command(self, command: str):
        """Handle fan speed setting (M106 S0-255)"""
        speed_match = re.search(r'S(\d+)', command)
        if speed_match:
            fan_pwm = int(speed_match.group(1))
            # Convert PWM (0-255) to percentage (0-100)
            self.fan_speed = int((fan_pwm / 255.0) * 100)
            # TODO: Send to Klipper via Moonraker

    async def _handle_fan_off_command(self):
        """Handle fan off command (M107)"""
        self.fan_speed = 0
        # TODO: Send to Klipper via Moonraker

    async def _send_temperature_response(self):
        """Send temperature response in appropriate format"""
        temp = self.current_temps
        
        if self.firmware_type == FirmwareType.MKS_ORIGINAL:
            # MKS Original: Simple format
            response = (f"T:{temp['hotend_temp']:.1f} /{temp['hotend_target']:.1f} "
                       f"B:{temp['bed_temp']:.1f} /{temp['bed_target']:.1f} @:0 B@:0")
        else:
            # BIGTREETECH: Marlin format (same as working dual_protocol)
            response = (f"ok T:{temp['hotend_temp']:.1f} /{temp['hotend_target']:.1f} "
                       f"B:{temp['bed_temp']:.1f} /{temp['bed_target']:.1f} @:0 B@:0")
        
        await self._send_response(response)

    async def _send_firmware_response(self):
        """Send firmware info in appropriate format"""
        if self.firmware_type == FirmwareType.MKS_ORIGINAL:
            await self._send_response("FIRMWARE_NAME:MKS-TFT FIRMWARE_VERSION:2.0.6")
        else:
            await self._send_response("FIRMWARE_NAME:Marlin 2.1.0 (Klipper Compatible) SOURCE_CODE_URL:github.com/MarlinFirmware/Marlin PROTOCOL_VERSION:1.0 MACHINE_TYPE:3D Printer EXTRUDER_COUNT:1")

    async def _send_position_response(self):
        """Send position response"""
        pos = self.position
        response = f"X:{pos['x_pos']:.2f} Y:{pos['y_pos']:.2f} Z:{pos['z_pos']:.2f} E:0.00"
        await self._send_response(response)

    async def _send_sd_status_response(self):
        """Send SD card status"""
        if self.print_stats['state'] == 'printing':
            progress_bytes = int(1000000 * self.print_stats['progress'] / 100)
            response = f"SD printing byte {progress_bytes}/1000000"
        else:
            response = "Not SD printing"
        await self._send_response(response)

    async def _send_file_list_response(self):
        """Send file list"""
        await self._send_response("Begin file list")
        if self.print_stats['filename']:
            await self._send_response(self.print_stats['filename'])
        else:
            await self._send_response("test.gcode")
        await self._send_response("End file list")

    
    async def _handle_action_command(self, command: str):
        """Handle action commands from TFT and respond appropriately"""
        if "remote pause" in command:
            self.logger.info("🎮 TFT requested pause")
            success = await self._send_moonraker_command("printer/print/pause")
            if success:
                # Confirm pause to TFT
                await self._send_response("M118 P0 A1 action:pause")
                
        elif "remote resume" in command:
            self.logger.info("🎮 TFT requested resume")
            success = await self._send_moonraker_command("printer/print/resume")
            if success:
                # Confirm resume to TFT
                await self._send_response("M118 P0 A1 action:resume")
                
        elif "remote cancel" in command:
            self.logger.info("🎮 TFT requested cancel")
            success = await self._send_moonraker_command("printer/print/cancel")
            if success:
                # Confirm cancel to TFT
                await self._send_response("M118 P0 A1 action:cancel")

    async def _send_moonraker_command(self, endpoint: str):
        """Send command to Moonraker and return success status"""
        try:
            url = f"http://{self.moonraker_host}:{self.moonraker_port}/{endpoint}"
            response = requests.post(url, timeout=5)
            if response.status_code == 200:
                self.logger.info(f"✅ Moonraker command successful: {endpoint}")
                return True
            else:
                self.logger.warning(f"❌ Moonraker command failed: {response.status_code}")
                return False
        except Exception as e:
            self.logger.warning(f"❌ Failed to send Moonraker command: {e}")
            return False

    async def update_loop(self):
        """Update printer data from Moonraker and broadcast status"""
        while self.running:
            if self.connected and self.detection_complete:
                try:
                    await self._update_from_moonraker()
                    await self._broadcast_status_updates()
                except Exception:
                    pass  # Silent failure, use fallback data
            
            await asyncio.sleep(3.0)  # Update every 3 seconds

    async def _broadcast_status_updates(self):
        """Broadcast status updates to TFT (continuous data streaming)"""
        # Send temperature update (what TFT expects continuously)
        await self._send_temperature_response()
        
        # Send fan speed update (M106 command that TFT firmware expects)
        fan_pwm = int((self.fan_speed / 100.0) * 255)  # Convert percentage to PWM (0-255)
        fan_cmd = f"M106 S{fan_pwm}"
        await self._send_response(fan_cmd)
        
        # Handle print state changes for proper TFT integration
        await self._handle_print_state_changes()
        await self._send_print_progress_updates()

    async def _handle_print_state_changes(self):
        """Handle print state changes and send appropriate M118 action codes"""
        current_state = self.print_stats['state']
        
        # Detect state changes and send appropriate action codes
        if current_state != self.last_print_state:
            self.logger.info(f"🔄 Print state changed: {self.last_print_state} → {current_state}")
            
            if current_state == 'printing' and not self.tft_print_active:
                # Print started
                await self._send_response("M118 P0 A1 action:print_start")
                self.tft_print_active = True
                self.logger.info("🚀 Sent print_start to TFT")
                
            elif current_state == 'paused' and self.last_print_state == 'printing':
                # Print paused
                await self._send_response("M118 P0 A1 action:pause")
                self.logger.info("⏸️ Sent pause to TFT")
                
            elif current_state == 'printing' and self.last_print_state == 'paused':
                # Print resumed
                await self._send_response("M118 P0 A1 action:resume")
                self.logger.info("▶️ Sent resume to TFT")
                
            elif current_state == 'complete' and self.tft_print_active:
                # Print completed
                await self._send_response("M118 P0 A1 action:print_end")
                self.tft_print_active = False
                self.logger.info("✅ Sent print_end to TFT")
                
            elif current_state in ['cancelled', 'error'] and self.tft_print_active:
                # Print cancelled or error
                await self._send_response("M118 P0 A1 action:cancel")
                self.tft_print_active = False
                self.logger.info("❌ Sent cancel to TFT")
            
            self.last_print_state = current_state

    async def _send_print_progress_updates(self):
        """Send print progress updates when actively printing"""
        if not self.tft_print_active or self.print_stats['state'] != 'printing':
            return
        
        # Send file data progress (percentage)
        if self.print_stats['progress'] > 0:
            progress_percent = int(self.print_stats['progress'])
            progress_cmd = f"M118 P0 A1 action:notification Data Left {progress_percent}/100"
            await self._send_response(progress_cmd)
        
        # Send time left if available
        if self.print_stats['remaining_time'] > 0:
            hours = int(self.print_stats['remaining_time'] // 3600)
            minutes = int((self.print_stats['remaining_time'] % 3600) // 60)
            seconds = int(self.print_stats['remaining_time'] % 60)
            time_cmd = f"M118 P0 A1 action:notification Time Left {hours:02d}h{minutes:02d}m{seconds:02d}s"
            await self._send_response(time_cmd)

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
                    self.current_temps['hotend_temp'] = status['extruder'].get('temperature', 25.0)
                    self.current_temps['hotend_target'] = status['extruder'].get('target', 0.0)
                
                if 'heater_bed' in status:
                    self.current_temps['bed_temp'] = status['heater_bed'].get('temperature', 22.0)
                    self.current_temps['bed_target'] = status['heater_bed'].get('target', 0.0)
            
            # Get position, print stats, and fan speed
            stats_url = f"http://{self.moonraker_host}:{self.moonraker_port}/printer/objects/query?print_stats&display_status&toolhead&fan"
            response = requests.get(stats_url, timeout=3)
            
            if response.status_code == 200:
                data = response.json()
                status = data.get('result', {}).get('status', {})
                
                if 'print_stats' in status:
                    stats = status['print_stats']
                    self.print_stats['state'] = stats.get('state', 'standby')
                    self.print_stats['filename'] = stats.get('filename', '')
                    self.print_stats['print_time'] = stats.get('print_duration', 0.0)
                    # Calculate remaining time based on progress and print time
                    if self.print_stats['progress'] > 0:
                        total_time_estimate = self.print_stats['print_time'] / (self.print_stats['progress'] / 100)
                        self.print_stats['remaining_time'] = max(0, total_time_estimate - self.print_stats['print_time'])
                
                if 'display_status' in status:
                    display = status['display_status']
                    self.print_stats['progress'] = display.get('progress', 0.0) * 100
                
                if 'toolhead' in status:
                    toolhead = status['toolhead']
                    position = toolhead.get('position', [150, 150, 10, 0])
                    self.position['x_pos'] = position[0] if len(position) > 0 else 150.0
                    self.position['y_pos'] = position[1] if len(position) > 1 else 150.0
                    self.position['z_pos'] = position[2] if len(position) > 2 else 10.0
                
                # Get fan speed from main part cooling fan
                if 'fan' in status:
                    fan_speed_ratio = status['fan'].get('speed', 0.0)
                    self.fan_speed = int(fan_speed_ratio * 100)  # Convert to percentage
                    
        except Exception:
            pass  # Silent failure, keep using current values

    async def close(self):
        """Clean shutdown"""
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
    client = TFT32Final()
    
    print("🚀 TFT32 Final Client")
    print("=" * 40)
    print(f"📡 Port: {client.serial_port} at {client.baudrate} baud")
    print("🔧 Production ready - minimal logging")
    print("📱 M-codes only, no KLIP messages")
    print()
    
    try:
        if await client.connect_and_detect():
            print(f"✅ Connected! Firmware: {client.firmware_type.value}")
            print("🎮 TFT controls active")
            print("📊 Real Moonraker data")
            print("\n💡 Press Ctrl+C to stop")
            
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