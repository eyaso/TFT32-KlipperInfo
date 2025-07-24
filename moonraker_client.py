import requests
import websockets
import asyncio
import json
import logging
from typing import Dict, Optional, Any

class MoonrakerClient:
    """Client for communicating with Moonraker API"""
    
    def __init__(self, host: str = "localhost", port: int = 7125):
        self.host = host
        self.port = port
        self.base_url = f"http://{host}:{port}"
        self.ws_url = f"ws://{host}:{port}/websocket"
        self.session = requests.Session()
        self.logger = logging.getLogger(__name__)
        
    def get_printer_info(self) -> Optional[Dict[str, Any]]:
        """Get basic printer information"""
        try:
            response = self.session.get(f"{self.base_url}/printer/info")
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            self.logger.error(f"Failed to get printer info: {e}")
            return None
    
    def get_printer_status(self) -> Optional[Dict[str, Any]]:
        """Get current printer status including temperatures"""
        try:
            response = self.session.get(f"{self.base_url}/printer/objects/query?heater_bed&extruder&toolhead&print_stats&display_status&fan&gcode_move&motion_report")
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            self.logger.error(f"Failed to get printer status: {e}")
            return None
    
    def get_comprehensive_status(self) -> Dict[str, Any]:
        """Get comprehensive printer status for custom TFT display"""
        status = self.get_printer_status()
        comprehensive_data = {
            # Temperatures
            'bed_temp': 0.0,
            'bed_target': 0.0,
            'hotend_temp': 0.0,
            'hotend_target': 0.0,
            
            # Print Status
            'state': 'standby',
            'filename': '',
            'print_duration': 0.0,
            'progress': 0.0,
            'estimated_time': 0.0,
            
            # Layer Info
            'current_layer': 0,
            'total_layers': 0,
            
            # Speeds & Controls
            'print_speed': 100,
            'flow_rate': 100,
            'fan_speed': 0,
            
            # Position
            'x_pos': 0.0,
            'y_pos': 0.0,
            'z_pos': 0.0,
            
            # System
            'connection_status': 'connected'
        }
        
        if status and 'result' in status and 'status' in status['result']:
            status_data = status['result']['status']
            
            # Temperature data
            if 'heater_bed' in status_data:
                bed_data = status_data['heater_bed']
                comprehensive_data['bed_temp'] = bed_data.get('temperature', 0.0)
                comprehensive_data['bed_target'] = bed_data.get('target', 0.0)
            
            if 'extruder' in status_data:
                extruder_data = status_data['extruder']
                comprehensive_data['hotend_temp'] = extruder_data.get('temperature', 0.0)
                comprehensive_data['hotend_target'] = extruder_data.get('target', 0.0)
            
            # Print statistics
            if 'print_stats' in status_data:
                print_data = status_data['print_stats']
                comprehensive_data['state'] = print_data.get('state', 'standby')
                comprehensive_data['filename'] = print_data.get('filename', '')
                comprehensive_data['print_duration'] = print_data.get('print_duration', 0.0)
            
            # Display status (progress)
            if 'display_status' in status_data:
                display_data = status_data['display_status']
                comprehensive_data['progress'] = display_data.get('progress', 0.0) * 100
            
            # Fan speed
            if 'fan' in status_data:
                fan_data = status_data['fan']
                comprehensive_data['fan_speed'] = int(fan_data.get('speed', 0.0) * 100)
            
            # Motion and positioning
            if 'gcode_move' in status_data:
                gcode_data = status_data['gcode_move']
                comprehensive_data['print_speed'] = int(gcode_data.get('speed_factor', 1.0) * 100)
                comprehensive_data['flow_rate'] = int(gcode_data.get('extrude_factor', 1.0) * 100)
                
                # Position
                position = gcode_data.get('gcode_position', [0, 0, 0, 0])
                if len(position) >= 3:
                    comprehensive_data['x_pos'] = position[0]
                    comprehensive_data['y_pos'] = position[1]
                    comprehensive_data['z_pos'] = position[2]
            
            # Toolhead data
            if 'toolhead' in status_data:
                toolhead_data = status_data['toolhead']
                position = toolhead_data.get('position', [0, 0, 0, 0])
                if len(position) >= 3:
                    comprehensive_data['x_pos'] = position[0]
                    comprehensive_data['y_pos'] = position[1]
                    comprehensive_data['z_pos'] = position[2]
        
        # Get estimated time remaining
        if comprehensive_data['progress'] > 0 and comprehensive_data['print_duration'] > 0:
            total_estimated = comprehensive_data['print_duration'] / (comprehensive_data['progress'] / 100.0)
            comprehensive_data['estimated_time'] = total_estimated - comprehensive_data['print_duration']
        
        return comprehensive_data
    
    def get_temperatures(self) -> Dict[str, float]:
        """Get current temperatures for bed and hotend"""
        status = self.get_printer_status()
        temperatures = {
            'bed_temp': 0.0,
            'bed_target': 0.0,
            'hotend_temp': 0.0,
            'hotend_target': 0.0
        }
        
        if status and 'result' in status and 'status' in status['result']:
            status_data = status['result']['status']
            
            # Bed temperatures
            if 'heater_bed' in status_data:
                bed_data = status_data['heater_bed']
                temperatures['bed_temp'] = bed_data.get('temperature', 0.0)
                temperatures['bed_target'] = bed_data.get('target', 0.0)
            
            # Hotend temperatures
            if 'extruder' in status_data:
                extruder_data = status_data['extruder']
                temperatures['hotend_temp'] = extruder_data.get('temperature', 0.0)
                temperatures['hotend_target'] = extruder_data.get('target', 0.0)
        
        return temperatures
    
    def get_print_stats(self) -> Dict[str, Any]:
        """Get comprehensive print statistics for standard G-code protocol"""
        status = self.get_printer_status()
        stats = {
            'state': 'standby',
            'filename': '',
            'print_duration': 0.0,
            'total_duration': 0.0,
            'progress': 0.0,
            'current_layer': 0,
            'total_layers': 0,
            'position': [0, 0, 0, 0],
            'speed_factor': 100,
            'extrude_factor': 100,
            'fan_speed': 0
        }
        
        if status and 'result' in status and 'status' in status['result']:
            status_data = status['result']['status']
            
            # Print statistics
            if 'print_stats' in status_data:
                print_data = status_data['print_stats']
                stats['state'] = print_data.get('state', 'standby')
                stats['filename'] = print_data.get('filename', '')
                stats['print_duration'] = print_data.get('print_duration', 0.0)
                stats['total_duration'] = print_data.get('total_duration', 0.0)
            
            # Progress from display status
            if 'display_status' in status_data:
                display_data = status_data['display_status']
                stats['progress'] = display_data.get('progress', 0.0) * 100
            
            # Virtual SD card progress (alternative/more accurate)
            if 'virtual_sdcard' in status_data:
                vsd_data = status_data['virtual_sdcard']
                if vsd_data.get('progress', 0) > 0:
                    stats['progress'] = vsd_data.get('progress', 0.0) * 100
            
            # Position and speed data
            if 'gcode_move' in status_data:
                gcode_data = status_data['gcode_move']
                stats['position'] = gcode_data.get('gcode_position', [0, 0, 0, 0])
                stats['speed_factor'] = int(gcode_data.get('speed_factor', 1.0) * 100)
                stats['extrude_factor'] = int(gcode_data.get('extrude_factor', 1.0) * 100)
            
            # Fan speed
            if 'fan' in status_data:
                fan_data = status_data['fan']
                stats['fan_speed'] = int(fan_data.get('speed', 0.0) * 100)
            
            # Layer information (if available from plugins)
            if 'print_stats' in status_data:
                print_data = status_data['print_stats']
                # Some plugins provide layer information
                if 'info' in print_data:
                    info = print_data['info']
                    stats['current_layer'] = info.get('current_layer', 0)
                    stats['total_layers'] = info.get('total_layer', 0)
        
        return stats
    
    def is_connected(self) -> bool:
        """Check if connection to Moonraker is working"""
        try:
            response = self.session.get(f"{self.base_url}/server/info", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    async def connect_websocket(self, callback=None):
        """Connect to Moonraker websocket for real-time updates"""
        try:
            async with websockets.connect(self.ws_url) as websocket:
                # Subscribe to printer object updates
                subscribe_msg = {
                    "jsonrpc": "2.0",
                    "method": "printer.objects.subscribe",
                    "params": {
                        "objects": {
                            "heater_bed": ["temperature", "target"],
                            "extruder": ["temperature", "target"],
                            "print_stats": ["state", "filename", "print_duration"],
                            "display_status": ["progress"],
                            "fan": ["speed"],
                            "gcode_move": ["speed_factor", "extrude_factor", "gcode_position"],
                            "toolhead": ["position"]
                        }
                    },
                    "id": 1
                }
                
                await websocket.send(json.dumps(subscribe_msg))
                
                async for message in websocket:
                    data = json.loads(message)
                    if callback:
                        callback(data)
                        
        except Exception as e:
            self.logger.error(f"WebSocket connection failed: {e}") 