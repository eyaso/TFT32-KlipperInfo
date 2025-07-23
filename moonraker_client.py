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
            response = self.session.get(f"{self.base_url}/printer/objects/query?heater_bed&extruder&toolhead&print_stats")
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            self.logger.error(f"Failed to get printer status: {e}")
            return None
    
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
        """Get current print statistics"""
        status = self.get_printer_status()
        stats = {
            'state': 'standby',
            'filename': '',
            'print_duration': 0.0,
            'progress': 0.0
        }
        
        if status and 'result' in status and 'status' in status['result']:
            status_data = status['result']['status']
            
            if 'print_stats' in status_data:
                print_data = status_data['print_stats']
                stats['state'] = print_data.get('state', 'standby')
                stats['filename'] = print_data.get('filename', '')
                stats['print_duration'] = print_data.get('print_duration', 0.0)
            
            # Calculate progress if available
            if 'display_status' in status_data:
                display_data = status_data['display_status']
                stats['progress'] = display_data.get('progress', 0.0) * 100
        
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
                            "display_status": ["progress"]
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