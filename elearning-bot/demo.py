#!/usr/bin/env python3
"""
Demo script showing how to use the eLearning Bot Web Interface
"""

import webbrowser
import time
import subprocess
import sys
import os

def main():
    """Demo the web interface"""
    print("🚀 eLearning Bot Web Interface Demo")
    print("=" * 50)

    # Check if web dependencies are installed
    try:
        import flask
        import flask_socketio
        import eventlet
        print("✅ Web dependencies are installed")
    except ImportError as e:
        print(f"❌ Missing web dependencies: {e}")
        print("Run: pip install flask flask-socketio eventlet")
        return

    # Check if all bot modules can be imported
    try:
        sys.path.insert(0, os.path.dirname(__file__))
        import config
        import utils
        import auth
        import course
        import conditions
        import video
        import quiz
        print("✅ All bot modules imported successfully")
    except ImportError as e:
        print(f"❌ Missing bot modules: {e}")
        return

    print("\n📋 Demo Steps:")
    print("1. Web server will start on http://127.0.0.1:8080")
    print("2. Open your browser to the URL above")
    print("3. Use the web interface to control the bot")
    print("4. Press Ctrl+C in this terminal to stop the server")
    print("\n⚠️  Note: First run 'python setup.py' to configure credentials")
    print("=" * 50)

    # Ask user if they want to continue
    try:
        input("Press Enter to start the web interface (or Ctrl+C to cancel)...")
    except KeyboardInterrupt:
        print("\nDemo cancelled")
        return

    # Start the web interface
    try:
        from web_ui import run_web_ui

        # Auto-open browser after a short delay
        def open_browser():
            time.sleep(2)
            webbrowser.open('http://127.0.0.1:8080')

        import threading
        browser_thread = threading.Thread(target=open_browser, daemon=True)
        browser_thread.start()

        print("🌐 Starting web interface...")
        run_web_ui()

    except KeyboardInterrupt:
        print("\n🛑 Web interface stopped")
    except Exception as e:
        print(f"❌ Error starting web interface: {e}")

if __name__ == "__main__":
    main()