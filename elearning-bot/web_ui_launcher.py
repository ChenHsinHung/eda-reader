#!/usr/bin/env python3
"""
Web UI launcher script
"""

import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

def main():
    """Launch the web interface"""
    try:
        from web_ui import run_web_ui
        print("Starting eLearning Bot Web Interface...")
        print("Open your browser to: http://127.0.0.1:8080")
        print("Press Ctrl+C to stop the server")
        run_web_ui()
    except ImportError as e:
        print(f"Error: {e}")
        print("Please install required packages:")
        print("pip install flask flask-socketio eventlet")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nWeb interface stopped")
    except Exception as e:
        print(f"Error starting web interface: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()