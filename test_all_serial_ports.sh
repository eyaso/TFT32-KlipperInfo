#!/bin/bash

echo "🔍 Testing ALL available serial ports..."
echo "======================================="

# Find all possible serial ports
PORTS=$(ls /dev/tty{S,AMA,USB}* 2>/dev/null)

if [ -z "$PORTS" ]; then
    echo "❌ No serial ports found!"
    echo "Available tty devices:"
    ls /dev/tty* | grep -E "(tty[SAMA]|ttyUSB)" | head -10
    exit 1
fi

echo "📡 Found serial ports:"
for port in $PORTS; do
    echo "  - $port"
done

echo ""
echo "🧪 Testing each port for 10 seconds..."

for port in $PORTS; do
    echo "======================================="
    echo "🔍 Testing $port at 250000 baud..."
    
    # Test if we can open the port
    if python3 -c "
import serial
import time
try:
    ser = serial.Serial('$port', 250000, timeout=1)
    print('✅ Opened $port successfully')
    print('📡 Listening for 10 seconds...')
    print('🎮 Send M105 from TFT Terminal NOW!')
    
    start_time = time.time()
    total_bytes = 0
    
    while time.time() - start_time < 10:
        if ser.in_waiting > 0:
            data = ser.read(ser.in_waiting)
            total_bytes += len(data)
            print(f'📥 RECEIVED: {data}')
            print(f'📝 TEXT: {data.decode(\"utf-8\", errors=\"replace\").strip()}')
        time.sleep(0.1)
    
    print(f'📊 Total bytes received: {total_bytes}')
    if total_bytes > 0:
        print('🎉 SUCCESS! This port receives data!')
    else:
        print('❌ No data received on this port')
    
    ser.close()
except Exception as e:
    print(f'❌ Error with $port: {e}')
print()
" 2>/dev/null; then
        echo ""
    else
        echo "❌ Cannot access $port"
    fi
done

echo "======================================="
echo "🎯 Test complete!"
echo "📱 If you saw data on any port, update config.py:"
echo "   TFT32_SERIAL_PORT = '/dev/WORKING_PORT'" 