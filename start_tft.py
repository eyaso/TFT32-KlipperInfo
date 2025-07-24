#!/usr/bin/env python3
"""
Simple starter for TFT32 Final Client
"""

import asyncio
import sys
import os

# Add current directory to path to import modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tft32_final import main

if __name__ == "__main__":
    print("🚀 Starting TFT32 Final Client...")
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 