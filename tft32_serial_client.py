#!/usr/bin/env python3
"""
MKS TFT32 Serial Client for Klipper
Communicates with MKS TFT32 using existing firmware by emulating printer responses
"""

import serial
import time
import logging
import threading
from typing import Dict, Optional
import re

class TFT32SerialClient:
    """Client for communicating with MKS TFT32 over serial"""
    
    def __init__(self, port: str = "/dev/ttyS0", baudrate: int = 115200):
        self.port = port
        self.baudrate = baudrate
        self.serial_conn = None
        self.logger = logging.getLogger(__name__)
        self.running = False
        self.read_thread = None
        
        # Current printer state to send to TFT
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
            'print_time': 0
        }
        
        # Comprehensive data for custom TFT screen
        self.comprehensive_data = {}
        
    def connect(self) -> bool:
        """Connect to TFT32 via serial"""
        try:
            self.serial_conn = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=1,
                xonxoff=False,
                rtscts=False,
                dsrdtr=False
            )
            
            self.logger.info(f"Connected to TFT32 on {self.port} at {self.baudrate} baud")
            
            # Start communication thread
            self.running = True
            self.read_thread = threading.Thread(target=self._communication_loop)
            self.read_thread.daemon = True
            self.read_thread.start()
            
            # Send initial status
            self._send_status_update()
            
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
        """Main communication loop to handle TFT commands"""
        last_temp_send = 0
        last_comprehensive_send = 0
        temp_send_interval = 2.0  # Send temperatures every 2 seconds
        comprehensive_send_interval = 1.0  # Send comprehensive data every 1 second
        
        while self.running and self.serial_conn and self.serial_conn.is_open:
            try:
                current_time = time.time()
                
                # Check for incoming commands from TFT
                if self.serial_conn.in_waiting > 0:
                    line = self.serial_conn.readline().decode('utf-8', errors='ignore').strip()
                    if line:
                        self._handle_tft_command(line)
                
                # Send periodic temperature updates for standard screens
                if current_time - last_temp_send >= temp_send_interval:
                    self._send_temperature_response()
                    last_temp_send = current_time
                    self.logger.debug("Sent periodic temperature update to TFT")
                
                # Send comprehensive data for custom screen
                if current_time - last_comprehensive_send >= comprehensive_send_interval:
                    self._send_comprehensive_data()
                    last_comprehensive_send = current_time
                    self.logger.debug("Sent comprehensive data to TFT")
                
                time.sleep(0.1)
                
            except Exception as e:
                self.logger.error(f"Error in communication loop: {e}")
                time.sleep(1)
    
    def _send_comprehensive_data(self):
        """Send comprehensive printer data for custom TFT screen"""
        if not self.comprehensive_data:
            return
            
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
        
        # Create comprehensive data string
        # Format: KLIP:hotend_temp:hotend_target:bed_temp:bed_target:state:progress:x_pos:y_pos:z_pos:elapsed/remaining:filename:print_speed:flow_rate:fan_speed
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
            f"{data.get('fan_speed', 0)}\r\n"
        )
        
        self._send_response(comprehensive_string)
    
    def _handle_tft_command(self, command: str):
        """Handle commands received from TFT32"""
        self.logger.debug(f"TFT Command: {command}")
        
        # Check for custom screen request
        if command.startswith('M999'):  # Custom command for comprehensive data request
            self._send_comprehensive_data()
            return
        
        # Common G-code commands that TFT might send
        if command.startswith('M105'):  # Temperature request
            self._send_temperature_response()
        elif command.startswith('M114'):  # Position request
            self._send_position_response()
        elif command.startswith('M27'):   # SD card print status
            self._send_sd_status_response()
        elif command.startswith('M20'):   # List SD card files
            self._send_file_list_response()
        elif command.startswith('G28'):   # Home command
            self._send_ok_response()
        elif command.startswith('M104') or command.startswith('M109'):  # Set hotend temp
            temp_match = re.search(r'S(\d+)', command)
            if temp_match:
                target_temp = float(temp_match.group(1))
                self.current_temps['hotend_target'] = target_temp
                self.logger.info(f"TFT set hotend target: {target_temp}°C")
            self._send_ok_response()
        elif command.startswith('M140') or command.startswith('M190'):  # Set bed temp
            temp_match = re.search(r'S(\d+)', command)
            if temp_match:
                target_temp = float(temp_match.group(1))
                self.current_temps['bed_target'] = target_temp
                self.logger.info(f"TFT set bed target: {target_temp}°C")
            self._send_ok_response()
        else:
            # Default response for unknown commands
            self._send_ok_response()
    
    def _send_temperature_response(self):
        """Send temperature status to TFT (M105 response)"""
        response = (f"T:{self.current_temps['hotend_temp']:.1f} /"
                   f"{self.current_temps['hotend_target']:.1f} "
                   f"B:{self.current_temps['bed_temp']:.1f} /"
                   f"{self.current_temps['bed_target']:.1f} @:0 B@:0\r\n")
        self._send_response(response)
    
    def _send_position_response(self):
        """Send position status to TFT (M114 response)"""
        if self.comprehensive_data:
            x = self.comprehensive_data.get('x_pos', 0.0)
            y = self.comprehensive_data.get('y_pos', 0.0)  
            z = self.comprehensive_data.get('z_pos', 0.0)
            response = f"X:{x:.2f} Y:{y:.2f} Z:{z:.2f} E:0.00 Count X:0 Y:0 Z:0\r\n"
        else:
            response = "X:0.00 Y:0.00 Z:0.00 E:0.00 Count X:0 Y:0 Z:0\r\n"
        self._send_response(response)
    
    def _send_sd_status_response(self):
        """Send SD card status to TFT (M27 response)"""
        if self.print_status['state'] == 'printing':
            # Calculate bytes printed based on progress
            total_bytes = 1000000  # Dummy value
            printed_bytes = int(total_bytes * self.print_status['progress'] / 100)
            response = f"SD printing byte {printed_bytes}/{total_bytes}\r\n"
        else:
            response = "Not SD printing\r\n"
        self._send_response(response)
    
    def _send_file_list_response(self):
        """Send file list to TFT (M20 response)"""
        response = "Begin file list\r\n"
        if self.print_status['filename']:
            response += f"{self.print_status['filename']}\r\n"
        else:
            response += "test_print.gcode\r\n"
            response += "calibration.gcode\r\n"
        response += "End file list\r\n"
        self._send_response(response)
    
    def _send_ok_response(self):
        """Send OK response to TFT"""
        self._send_response("ok\r\n")
    
    def _send_response(self, response: str):
        """Send response to TFT32"""
        try:
            if self.serial_conn and self.serial_conn.is_open:
                self.serial_conn.write(response.encode('utf-8'))
                self.serial_conn.flush()
                self.logger.debug(f"Sent to TFT: {response.strip()}")
        except Exception as e:
            self.logger.error(f"Error sending response: {e}")
    
    def _send_status_update(self):
        """Send periodic status updates to TFT"""
        # Some TFTs expect periodic temperature updates
        self._send_temperature_response()
    
    def update_temperatures(self, temps: Dict[str, float]):
        """Update temperature data from Moonraker"""
        self.current_temps.update(temps)
        self.logger.debug(f"Updated temperatures: {self.current_temps}")
    
    def update_print_status(self, status: Dict):
        """Update print status from Moonraker"""
        self.print_status.update(status)
        self.logger.debug(f"Updated print status: {self.print_status}")
    
    def update_comprehensive_data(self, data: Dict):
        """Update comprehensive data for custom TFT screen"""
        self.comprehensive_data = data
        # Also update legacy data for compatibility
        self.current_temps.update({
            'hotend_temp': data.get('hotend_temp', 0.0),
            'hotend_target': data.get('hotend_target', 0.0),
            'bed_temp': data.get('bed_temp', 0.0),
            'bed_target': data.get('bed_target', 0.0)
        })
        self.print_status.update({
            'state': data.get('state', 'standby'),
            'progress': data.get('progress', 0.0),
            'filename': data.get('filename', ''),
            'print_time': data.get('print_duration', 0.0)
        })
        self.logger.debug(f"Updated comprehensive data: {len(str(data))} characters")
    
    def is_connected(self) -> bool:
        """Check if connected to TFT32"""
        return (self.serial_conn is not None and 
                self.serial_conn.is_open and 
                self.running) 