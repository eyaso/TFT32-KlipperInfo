#!/usr/bin/env python3
"""
TFT32 Standard G-code Client for Klipper
Uses built-in BIGTREETECH firmware G-code protocol instead of custom KLIP protocol
"""

import serial
import time
import logging
import threading
from typing import Dict, Optional
import re
import config

class TFT32StandardClient:
    """Client for communicating with TFT32 using standard G-code protocol"""
    
    def __init__(self, port: str = None, baudrate: int = None):
        self.port = port or config.TFT32_SERIAL_PORT
        self.baudrate = baudrate or config.TFT32_BAUDRATE
        self.serial_conn = None
        self.logger = logging.getLogger(__name__)
        self.running = False
        self.read_thread = None
        
        # Current printer state
        self.current_temps = {
            'hotend_temp': 0.0,
            'hotend_target': 0.0,
            'bed_temp': 0.0,
            'bed_target': 0.0
        }
        
        self.print_status = {
            'state': 'standby',
            'progress': 0.0,
            'filename': '',
            'print_time': 0.0,
            'remaining_time': 0,
            'current_layer': None,
            'total_layers': None
        }
        
        self.last_print_state = 'standby'
        
    def connect(self) -> bool:
        """Connect to TFT32"""
        try:
            self.serial_conn = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=1,
                write_timeout=2,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE
            )
            
            self.running = True
            self.read_thread = threading.Thread(target=self._communication_loop, daemon=True)
            self.read_thread.start()
            
            self.logger.info(f"Connected to TFT32 on {self.port} at {self.baudrate} baud")
            
            # Send initial handshake sequence to wake up TFT
            time.sleep(0.5)  # Let connection settle
            self._send_initial_handshake()
            
            return True
        except Exception as e:
            self.logger.error(f"Failed to connect to TFT32: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from TFT32"""
        self.running = False
        if self.read_thread:
            self.read_thread.join(timeout=2)
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.close()
        self.logger.info("Disconnected from TFT32")
    
    def _communication_loop(self):
        """Main communication loop"""
        temp_send_interval = 2.0   # Send temperature every 2 seconds
        last_temp_send = 0
        status_send_interval = 1.0  # Send status every 1 second
        last_status_send = 0
        debug_interval = 30.0  # Debug message every 30 seconds
        last_debug = 0
        first_command_received = False  # Track if TFT has started communicating
        
        while self.running:
            try:
                current_time = time.time()
                
                # Debug message every 30 seconds
                if current_time - last_debug >= debug_interval:
                    status = "🟢 ACTIVE" if first_command_received else "🟡 WAITING FOR TFT"
                    self.logger.info(f"🔄 Communication loop active - TFT status: {status}")
                    last_debug = current_time
                
                # Handle incoming data from TFT
                if self.serial_conn.in_waiting > 0:
                    line = self.serial_conn.readline().decode('utf-8', errors='ignore').strip()
                    if line:
                        if not first_command_received:
                            self.logger.info("🎉 TFT HAS STARTED COMMUNICATING! Connection established.")
                            first_command_received = True
                        self.logger.info(f"📥 TFT >> PI: '{line}'")  # Show received messages
                        self._handle_tft_command(line)
                
                # Send periodic temperature updates (M105 response format)
                if current_time - last_temp_send >= temp_send_interval:
                    self._send_temperature_response()
                    last_temp_send = current_time
                
                # Send status updates
                if current_time - last_status_send >= status_send_interval:
                    self._send_status_updates()
                    last_status_send = current_time
                
                time.sleep(0.1)
                
            except Exception as e:
                self.logger.error(f"Error in communication loop: {e}")
                time.sleep(1)
    
    def _handle_tft_command(self, command: str):
        """Handle commands received from TFT32"""
        # Command processing (already logged in communication loop)
        
        # Standard G-code commands that TFT sends
        if command.startswith('M105'):  # Temperature request
            self.logger.info("🌡️ TFT requesting temperature - sending current data")
            self._send_temperature_response()
        elif command.startswith('M114'):  # Position request
            self.logger.info("📍 TFT requesting position")
            self._send_position_response()
        elif command.startswith('M27'):   # SD card print status
            self.logger.info("💾 TFT requesting SD status")
            self._send_sd_status_response()
        elif command.startswith('M20'):   # List SD files
            self.logger.info("📂 TFT requesting file list")
            self._send_file_list_response()
        elif command.startswith('M115'):  # Get firmware info
            self.logger.info("🔧 TFT requesting firmware info")
            self._send_firmware_response()
        elif command.startswith('G28'):   # Home command
            self.logger.info("🏠 TFT requesting home - forwarding to Klipper")
            # TODO: Future enhancement - forward to Klipper for actual homing
            self._send_ok_response()
        elif command.startswith('M104') or command.startswith('M109'):  # Set hotend temp
            self.logger.info(f"🔥 TFT setting hotend temperature: {command}")
            # TODO: Future enhancement - parse temperature and send to Klipper
            self._send_ok_response()
        elif command.startswith('M140') or command.startswith('M190'):  # Set bed temp
            self.logger.info(f"🛏️ TFT setting bed temperature: {command}")
            # TODO: Future enhancement - parse temperature and send to Klipper
            self._send_ok_response()
        elif command.startswith('M106') or command.startswith('M107'):  # Fan control
            self.logger.info(f"💨 TFT controlling fan: {command}")
            # TODO: Future enhancement - forward to Klipper
            self._send_ok_response()
        # TODO: Add more G-code commands for printer control:
        #       G0/G1 (move), G91/G90 (positioning mode), etc.
        else:
            self.logger.info(f"❓ TFT sent unknown/other command: {command}")
            # Generic OK response for other commands
            self._send_ok_response()
    
    def _send_temperature_response(self):
        """Send temperature data in standard M105 response format"""
        # BIGTREETECH firmware expects "ok" prefix for M105 responses
        response = (f"ok T:{self.current_temps['hotend_temp']:.1f} /"
                    f"{self.current_temps['hotend_target']:.1f} "
                    f"B:{self.current_temps['bed_temp']:.1f} /"
                    f"{self.current_temps['bed_target']:.1f} @:0 B@:0\r\n")
        self._send_response(response)
    
    def _send_initial_handshake(self):
        """Send initial sequence to establish TFT connection"""
        self.logger.info("🤝 Sending initial handshake to TFT...")
        
        # Send initial temperature response to trigger connection detection
        self._send_response("ok T:25.0 /0.0 B:22.0 /0.0 @:0 B@:0\r\n")
        time.sleep(0.2)
        
        # Send firmware info
        self._send_response("FIRMWARE_NAME:Klipper-TFT32-Bridge FIRMWARE_VERSION:1.0.0 MACHINE_TYPE:Klipper EXTRUDER_COUNT:1\r\n")
        time.sleep(0.2)
        
        # Send OK to indicate ready
        self._send_response("ok\r\n")
        
        self.logger.info("🤝 Initial handshake sent - TFT should start responding...")
    
    def _send_position_response(self):
        """Send position data in standard M114 response format"""
        response = "X:150.00 Y:150.00 Z:10.00 E:0.00 Count X:12000 Y:12000 Z:4000\r\n"
        self._send_response(response)
    
    def _send_sd_status_response(self):
        """Send SD print status"""
        if self.print_status['state'] == 'printing':
            response = f"SD printing byte {int(self.print_status['progress'])}% complete\r\n"
        else:
            response = "Not SD printing\r\n"
        self._send_response(response)
    
    def _send_file_list_response(self):
        """Send file list response"""
        response = "Begin file list\r\ntest.gcode\r\nEnd file list\r\n"
        self._send_response(response)
    
    def _send_status_updates(self):
        """Send print status updates using standard G-codes"""
        current_state = self.print_status['state']
        
        # Send state change notifications
        if current_state != self.last_print_state:
            if current_state == 'printing' and self.last_print_state != 'printing':
                self._send_response("M118 P0 A1 action:print_start\r\n")
            elif current_state == 'paused':
                self._send_response("M118 P0 A1 action:pause\r\n")
            elif current_state == 'standby' and self.last_print_state == 'printing':
                self._send_response("M118 P0 A1 action:print_end\r\n")
            elif current_state == 'cancelled':
                self._send_response("M118 P0 A1 action:cancel\r\n")
            
            self.last_print_state = current_state
        
        # Send progress information during printing
        if current_state == 'printing':
            # Time remaining (BTT TFT format: M118 P0 A1 action:notification Time Left HHhMMmSSs)
            if self.print_status['remaining_time'] > 0:
                hours = self.print_status['remaining_time'] // 3600
                minutes = (self.print_status['remaining_time'] % 3600) // 60
                seconds = self.print_status['remaining_time'] % 60
                time_str = f"{hours:02d}h{minutes:02d}m{seconds:02d}s"
                self._send_response(f"M118 P0 A1 action:notification Time Left {time_str}\r\n")
            
            # Layer progress (BTT TFT format: M118 P0 A1 action:notification Layer Left XX/YY)
            if self.print_status['total_layers'] and self.print_status['total_layers'] > 0:
                layer_str = f"{self.print_status['current_layer'] or 0}/{self.print_status['total_layers']}"
                self._send_response(f"M118 P0 A1 action:notification Layer Left {layer_str}\r\n")
            
            # File progress (BTT TFT format: M118 P0 A1 action:notification Data Left XX/100)
            if self.print_status['progress'] > 0:
                progress_str = f"{int(self.print_status['progress'])}/100"
                self._send_response(f"M118 P0 A1 action:notification Data Left {progress_str}\r\n")
    
    def _send_firmware_response(self):
        """Send firmware identification response for M115"""
        response = ("FIRMWARE_NAME:Klipper-TFT32-Bridge "
                   "FIRMWARE_VERSION:1.0.0 "
                   "MACHINE_TYPE:Klipper "
                   "EXTRUDER_COUNT:1\r\n")
        self._send_response(response)
    
    def _send_ok_response(self):
        """Send standard OK response"""
        self._send_response("ok\r\n")
    
    def _send_response(self, response: str):
        """Send response to TFT32"""
        try:
            if self.serial_conn and self.serial_conn.is_open:
                self.logger.info(f"📤 PI >> TFT: '{response.strip()}'")  # Show sent messages
                self.serial_conn.write(response.encode('utf-8'))
                self.serial_conn.flush()
        except Exception as e:
            self.logger.error(f"Failed to send response: {e}")
    
    def update_temperatures(self, temps: Dict[str, float]):
        """Update temperature data"""
        self.current_temps.update(temps)
        self.logger.debug(f"Updated temperatures: {self.current_temps}")
    
    def update_print_status(self, status: Dict):
        """Update print status data"""
        self.print_status.update(status)
        self.logger.debug(f"Updated print status: {self.print_status}")
    
    def is_connected(self) -> bool:
        """Check if connected to TFT32"""
        return (self.serial_conn is not None and 
                self.serial_conn.is_open and 
                self.running) 