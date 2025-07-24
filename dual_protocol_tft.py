#!/usr/bin/env python3
"""
Dual Protocol TFT32 Client
Supports both MKS Original Firmware and BIGTREETECH Firmware
Auto-detects firmware type and uses appropriate protocol
"""

import serial
import time
import logging
import asyncio
import requests
import json
import re
from enum import Enum
from typing import Optional, Dict, Any

class FirmwareType(Enum):
    UNKNOWN = "unknown"
    MKS_ORIGINAL = "mks_original"  # Original Keil-based MKS firmware
    BIGTREETECH = "bigtreetech"    # BIGTREETECH firmware

class DualProtocolTFT:
    def __init__(self, serial_port: str = '/dev/ttyS0', baudrate: int = 250000):
        self.serial_port = serial_port
        self.baudrate = baudrate
        self.serial_conn: Optional[serial.Serial] = None
        self.connected = False
        self.running = False
        
        # Firmware detection
        self.firmware_type = FirmwareType.UNKNOWN
        self.detection_complete = False
        
        # State
        self.current_temps = {
            'hotend_temp': 25.0,
            'hotend_target': 0.0,
            'bed_temp': 22.0,
            'bed_target': 0.0
        }
        self.print_stats = {
            'state': 'standby',
            'progress': 75.0,
            'filename': 'test_print.gcode',
            'print_time': 4500.0,  # 75 minutes
            'remaining_time': 1500  # 25 minutes
        }
        
        # Comprehensive data for custom TFT screen (like working version)
        self.comprehensive_data = {
            'hotend_temp': 25.0,
            'hotend_target': 0.0,
            'bed_temp': 22.0,
            'bed_target': 0.0,
            'state': 'printing',
            'progress': 75.0,
            'x_pos': 125.5,
            'y_pos': 89.2,
            'z_pos': 15.75,
            'print_duration': 4500.0,
            'estimated_time': 1500.0,
            'filename': 'test_print.gcode',
            'print_speed': 100,
            'flow_rate': 100,
            'fan_speed': 50
        }
        
        # Setup logging
        self.logger = logging.getLogger('DualProtocolTFT')
        self.logger.setLevel(logging.INFO)
        
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
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
            self.logger.info(f"🔌 Connected to {self.serial_port} at {self.baudrate} baud")
            
            # Start detection process
            await self._detect_firmware()
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Failed to connect: {e}")
            self.connected = False
            return False

    async def _detect_firmware(self):
        """Detect firmware type by analyzing initial communication"""
        self.logger.info("🔍 Detecting TFT firmware type...")
        
        # Wait for initial commands from TFT
        detection_timeout = 10  # seconds
        start_time = time.time()
        received_commands = []
        
        while time.time() - start_time < detection_timeout and not self.detection_complete:
            if self.serial_conn and self.serial_conn.in_waiting > 0:
                try:
                    incoming = self.serial_conn.readline().decode('utf-8', errors='ignore').strip()
                    if incoming:
                        received_commands.append(incoming)
                        self.logger.info(f"📥 Received: '{incoming}'")
                        
                        # Try to detect based on command format
                        if self._analyze_command_for_detection(incoming):
                            break
                        
                        # Respond to keep communication alive
                        await self._send_generic_response(incoming)
                        
                except Exception as e:
                    self.logger.error(f"Detection error: {e}")
            
            await asyncio.sleep(0.1)
        
        # If no clear detection, default to BIGTREETECH
        if self.firmware_type == FirmwareType.UNKNOWN:
            self.logger.warning("⚠️ Could not detect firmware type, defaulting to BIGTREETECH")
            self.firmware_type = FirmwareType.BIGTREETECH
        
        self.detection_complete = True
        self.logger.info(f"🎯 Detected firmware: {self.firmware_type.value}")
        
        # Send appropriate initial handshake
        await self._send_initial_handshake()

    def _analyze_command_for_detection(self, command: str) -> bool:
        """Analyze command to detect firmware type"""
        
        # BIGTREETECH firmware characteristics
        if any(pattern in command for pattern in ['>>N', '*', 'M105*', 'checksum']):
            self.firmware_type = FirmwareType.BIGTREETECH
            self.logger.info("✅ Detected BIGTREETECH firmware (checksums/line numbers)")
            return True
        
        # Simple M105 without checksums suggests original MKS
        if command.strip() == 'M105' or command.startswith('M105') and '*' not in command:
            self.firmware_type = FirmwareType.MKS_ORIGINAL
            self.logger.info("✅ Detected MKS Original firmware (simple commands)")
            return True
        
        return False

    async def _send_generic_response(self, command: str):
        """Send a generic response during detection phase"""
        if 'M105' in command:
            # Send temperature in both formats to see what works
            await self._send_response("T:25.0 /0.0 B:22.0 /0.0")  # MKS format
            await asyncio.sleep(0.1)
            await self._send_response("ok T:25.0 /0.0 B:22.0 /0.0 @:0 B@:0")  # BTT format
        else:
            await self._send_response("ok")

    async def _send_initial_handshake(self):
        """Send initial handshake based on detected firmware"""
        self.logger.info(f"🤝 Sending {self.firmware_type.value} handshake...")
        
        if self.firmware_type == FirmwareType.MKS_ORIGINAL:
            await self._send_mks_handshake()
        else:  # BIGTREETECH
            await self._send_btt_handshake()

    async def _send_mks_handshake(self):
        """Send handshake for MKS Original firmware"""
        self.logger.info("📤 MKS Original handshake")
        
        # MKS firmware expects simple responses
        await self._send_response("T:25.0 /0.0 B:22.0 /0.0")
        await asyncio.sleep(0.2)
        
        # Basic firmware info
        await self._send_response("FIRMWARE_NAME:MKS-TFT FIRMWARE_VERSION:2.0.6")
        await asyncio.sleep(0.1)
        
        await self._send_response("ok")

    async def _send_btt_handshake(self):
        """Send handshake for BIGTREETECH firmware"""
        self.logger.info("📤 BIGTREETECH handshake")
        
        # BTT firmware expects Marlin-style responses
        await self._send_response("ok T:25.0 /0.0 B:22.0 /0.0 @:0 B@:0")
        await asyncio.sleep(0.2)
        
        # Firmware with capabilities
        await self._send_response("FIRMWARE_NAME:Klipper HOST_ACTION_COMMANDS:1 EXTRUDER_COUNT:1")
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

    async def communication_loop(self):
        """Main communication loop"""
        self.logger.info("🔄 Starting communication loop")
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
        """Handle incoming commands based on firmware type"""
        self.logger.info(f"📥 TFT >> PI: '{command}'")
        
        # Check for custom screen request (from working version)
        if command.startswith('M999'):  # Custom command for comprehensive data request
            await self._send_comprehensive_data()
            return
        
        if 'M105' in command:
            await self._send_temperature_response()
        elif 'M115' in command:
            await self._send_firmware_response()
        elif 'M114' in command:
            await self._send_position_response()
        elif 'M27' in command:   # SD card print status
            await self._send_sd_status_response()
        elif 'M20' in command:   # List SD card files
            await self._send_file_list_response()
        elif 'M92' in command:
            await self._send_response("M92 X80.00 Y80.00 Z400.00 E420.00")
            if self.firmware_type == FirmwareType.BIGTREETECH:
                await self._send_response("ok")
        elif command.startswith('M104') or command.startswith('M109'):  # Set hotend temp
            temp_match = re.search(r'S(\d+)', command)
            if temp_match:
                target_temp = float(temp_match.group(1))
                self.current_temps['hotend_target'] = target_temp
                self.comprehensive_data['hotend_target'] = target_temp
                self.logger.info(f"🔥 TFT set hotend target: {target_temp}°C")
            if self.firmware_type == FirmwareType.BIGTREETECH:
                await self._send_response("ok")
        elif command.startswith('M140') or command.startswith('M190'):  # Set bed temp
            temp_match = re.search(r'S(\d+)', command)
            if temp_match:
                target_temp = float(temp_match.group(1))
                self.current_temps['bed_target'] = target_temp
                self.comprehensive_data['bed_target'] = target_temp
                self.logger.info(f"🛏️ TFT set bed target: {target_temp}°C")
            if self.firmware_type == FirmwareType.BIGTREETECH:
                await self._send_response("ok")
        elif command.startswith('G28'):   # Home command
            self.logger.info("🏠 TFT requested home")
            if self.firmware_type == FirmwareType.BIGTREETECH:
                await self._send_response("ok")
        elif 'action:' in command:
            await self._handle_action_command(command)
        else:
            if self.firmware_type == FirmwareType.BIGTREETECH:
                await self._send_response("ok")

    async def _send_temperature_response(self):
        """Send temperature response in appropriate format"""
        temp = self.current_temps
        
        if self.firmware_type == FirmwareType.MKS_ORIGINAL:
            # MKS Original: Simple format without 'ok' or '@' (but keep @:0 B@:0 for compatibility)
            response = (f"T:{temp['hotend_temp']:.1f} /{temp['hotend_target']:.1f} "
                       f"B:{temp['bed_temp']:.1f} /{temp['bed_target']:.1f} @:0 B@:0")
        else:
            # BIGTREETECH: Full Marlin format
            response = (f"ok T:{temp['hotend_temp']:.1f} /{temp['hotend_target']:.1f} "
                       f"B:{temp['bed_temp']:.1f} /{temp['bed_target']:.1f} @:0 B@:0")
        
        await self._send_response(response)

    async def _send_firmware_response(self):
        """Send firmware info in appropriate format"""
        if self.firmware_type == FirmwareType.MKS_ORIGINAL:
            await self._send_response("FIRMWARE_NAME:MKS-TFT FIRMWARE_VERSION:2.0.6")
        else:
            await self._send_response("FIRMWARE_NAME:Klipper HOST_ACTION_COMMANDS:1 EXTRUDER_COUNT:1")
            await self._send_response("ok")

    async def _send_position_response(self):
        """Send position response"""
        await self._send_response("X:150.00 Y:150.00 Z:10.00 E:0.00")
        if self.firmware_type == FirmwareType.BIGTREETECH:
            await self._send_response("ok")

    async def _send_sd_status_response(self):
        """Send SD card status to TFT (M27 response)"""
        if self.print_stats['state'] == 'printing':
            # Calculate bytes printed based on progress
            total_bytes = 1000000  # Dummy value
            printed_bytes = int(total_bytes * self.print_stats['progress'] / 100)
            response = f"SD printing byte {printed_bytes}/{total_bytes}"
        else:
            response = "Not SD printing"
        await self._send_response(response)

    async def _send_file_list_response(self):
        """Send file list to TFT (M20 response)"""
        await self._send_response("Begin file list")
        if self.print_stats['filename']:
            await self._send_response(self.print_stats['filename'])
        else:
            await self._send_response("test_print.gcode")
            await self._send_response("calibration.gcode")
        await self._send_response("End file list")

    async def _send_comprehensive_data(self):
        """Send comprehensive printer data for custom TFT screen (KLIP format)"""
        data = self.comprehensive_data
        
        # Format time as HH:MM
        elapsed_hours = int(data.get('print_duration', 0) // 3600)
        elapsed_mins = int((data.get('print_duration', 0) % 3600) // 60)
        elapsed_time = f"{elapsed_hours:02d}:{elapsed_mins:02d}"
        
        remaining_hours = int(data.get('estimated_time', 0) // 3600)
        remaining_mins = int((data.get('estimated_time', 0) % 3600) // 60)
        remaining_time = f"{remaining_hours:02d}:{remaining_mins:02d}"
        
        # Clean filename (remove path and limit length)
        filename = data.get('filename', 'No file')
        if '/' in filename:
            filename = filename.split('/')[-1]
        if len(filename) > 20:
            filename = filename[:17] + "..."
        
        # Create comprehensive data string (KLIP format from working version)
        comprehensive_string = (
            f"KLIP:"
            f"{data.get('hotend_temp', 0):.1f}:"
            f"{data.get('hotend_target', 0):.1f}:"
            f"{data.get('bed_temp', 0):.1f}:"
            f"{data.get('bed_target', 0):.1f}:"
            f"{data.get('state', 'standby')}:"
            f"{data.get('progress', 0):.0f}:"
            f"{data.get('x_pos', 0):.2f}:"
            f"{data.get('y_pos', 0):.2f}:"
            f"{data.get('z_pos', 0):.2f}:"
            f"{elapsed_time}/{remaining_time}:"
            f"{filename}:"
            f"{data.get('print_speed', 100)}:"
            f"{data.get('flow_rate', 100)}:"
            f"{data.get('fan_speed', 0)}"
        )
        
        await self._send_response(comprehensive_string)
        self.logger.info("📤 Sent KLIP comprehensive data")

    async def _handle_action_command(self, command: str):
        """Handle action commands (BTT firmware)"""
        if "remote pause" in command:
            self.logger.info("🎮 TFT requested pause")
        elif "remote resume" in command:
            self.logger.info("🎮 TFT requested resume")
        elif "remote cancel" in command:
            self.logger.info("🎮 TFT requested cancel")

    async def update_loop(self):
        """Send periodic updates"""
        while self.running:
            if self.connected and self.detection_complete:
                try:
                    await self._send_status_updates()
                except Exception as e:
                    self.logger.error(f"Update error: {e}")
            
            await asyncio.sleep(3.0)  # Update every 3 seconds

    async def _send_status_updates(self):
        """Send status updates based on firmware type"""
        # Send comprehensive data for custom screen (like working version)
        await self._send_comprehensive_data()
        
        if self.firmware_type == FirmwareType.BIGTREETECH:
            # BTT firmware supports M118 notifications
            remaining_hours = int(self.print_stats['remaining_time'] // 3600)
            remaining_minutes = int((self.print_stats['remaining_time'] % 3600) // 60)
            remaining_seconds = int(self.print_stats['remaining_time'] % 60)
            
            time_cmd = f"M118 P0 A1 action:notification Time Left {remaining_hours:02d}h{remaining_minutes:02d}m{remaining_seconds:02d}s"
            progress_cmd = f"M118 P0 A1 action:notification Data Left {self.print_stats['progress']:.0f}/100"
            
            await self._send_response(time_cmd)
            await asyncio.sleep(0.1)
            await self._send_response(progress_cmd)
        
        # Always send periodic temperatures (both firmware types need this)
        await self._send_temperature_response()

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
    # Try to load config
    try:
        import config
        serial_port = getattr(config, 'TFT32_SERIAL_PORT', '/dev/ttyS0')
        baudrate = getattr(config, 'TFT32_BAUDRATE', 250000)
    except ImportError:
        serial_port = '/dev/ttyS0'
        baudrate = 250000
    
    print("🚀 Dual Protocol TFT32 Client")
    print("=" * 50)
    print(f"📡 Port: {serial_port} at {baudrate} baud")
    print("🔍 Auto-detecting firmware type...")
    print("📱 Supports both MKS Original and BIGTREETECH firmware")
    print()
    
    client = DualProtocolTFT(serial_port, baudrate)
    
    try:
        if await client.connect_and_detect():
            print(f"✅ Connected! Firmware: {client.firmware_type.value}")
            print("🎮 Try using TFT controls and check display")
            print("💡 Press Ctrl+C to stop")
            print()
            
            # Start communication and update loops
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