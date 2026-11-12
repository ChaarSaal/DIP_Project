"""
PixelSpec Entry Point
Run the local application:
    python run.py
    python run.py --port 8500
"""

import sys
import os

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from pixelspec.server.app import main

if __name__ == "__main__":
    main()
