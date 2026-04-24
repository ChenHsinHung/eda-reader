#!/usr/bin/env python3
"""
Web interface for elearning-bot
Provides a user-friendly GUI for controlling the bot
"""

import os
import json
import threading
import time
from datetime import datetime
from flask import Flask, render_template, request, jsonify, Response
from flask_socketio import SocketIO, emit
import logging

from config import *
from utils import setup_logging
from auth import AuthManager
from course import CourseNavigator
from encryption import get_credential_manager


class WebInterface:
    """Web interface for the elearning bot"""

    def __init__(self):
        self.app = Flask(__name__,
                        template_folder=os.path.join(os.path.dirname(__file__), 'templates'),
                        static_folder=os.path.join(os.path.dirname(__file__), 'static'))
        self.app.config['SECRET_KEY'] = WEB_SECRET_KEY
        self.socketio = SocketIO(self.app, cors_allowed_origins="*")

        self.logger = logging.getLogger('elearning_bot')
        self.bot_thread = None
        self.is_running = False
        self.current_status = "idle"
        self.progress_info = {
            'total_courses': 0,
            'completed_courses': 0,
            'current_course': "",
            'current_action': "",
            'logs': []
        }

        self.setup_routes()
        self.setup_socket_events()

    def setup_routes(self):
        """Setup Flask routes"""

        @self.app.route('/')
        def index():
            """Main dashboard page"""
            return render_template('index.html')

        @self.app.route('/api/status')
        def get_status():
            """Get current bot status"""
            return jsonify({
                'is_running': self.is_running,
                'status': self.current_status,
                'progress': self.progress_info
            })

        @self.app.route('/api/courses', methods=['GET'])
        def get_courses():
            """Get available courses"""
            try:
                # Quick login to get courses
                auth_manager = AuthManager()
                if not auth_manager.login():
                    return jsonify({'error': 'Login failed'}), 401

                driver = auth_manager.get_driver()
                navigator = CourseNavigator(driver)

                courses = navigator.get_course_list()
                auth_manager.cleanup()

                return jsonify({'courses': courses})
            except Exception as e:
                self.logger.error(f"Failed to get courses: {e}")
                return jsonify({'error': str(e)}), 500

        @self.app.route('/api/start', methods=['POST'])
        def start_bot():
            """Start the bot"""
            if self.is_running:
                return jsonify({'error': 'Bot is already running'}), 400

            data = request.get_json()
            courses = data.get('courses', [])
            max_courses = data.get('maxCourses', 0)

            # Start bot in background thread
            self.bot_thread = threading.Thread(
                target=self.run_bot,
                args=(courses, max_courses)
            )
            self.bot_thread.daemon = True
            self.bot_thread.start()

            return jsonify({'message': 'Bot started'})

        @self.app.route('/api/stop', methods=['POST'])
        def stop_bot():
            """Stop the bot"""
            self.is_running = False
            self.current_status = "stopping"
            self.socketio.emit('status_update', {
                'status': 'stopping',
                'message': 'Stopping bot...'
            })
            return jsonify({'message': 'Bot stopping'})

        @self.app.route('/api/logs')
        def get_logs():
            """Get recent logs"""
            try:
                log_file = self.get_latest_log_file()
                if log_file and os.path.exists(log_file):
                    with open(log_file, 'r', encoding='utf-8') as f:
                        logs = f.readlines()[-100:]  # Last 100 lines
                    return jsonify({'logs': logs})
                return jsonify({'logs': []})
            except Exception as e:
                return jsonify({'error': str(e)}), 500

        @self.app.route('/settings')
        def settings():
            """Settings page"""
            return render_template('settings.html')

        @self.app.route('/api/credentials', methods=['GET', 'POST', 'DELETE'])
        def credentials():
            """Manage credentials"""
            try:
                manager = get_credential_manager()

                if request.method == 'GET':
                    # Check if credentials exist
                    exists = manager.credentials_exist()
                    return jsonify({'exists': exists})

                elif request.method == 'POST':
                    # Save new credentials
                    data = request.get_json()
                    account_id = data.get('account_id', '').strip()
                    password = data.get('password', '').strip()
                    password_confirm = data.get('password_confirm', '').strip()

                    # Validate input
                    if not account_id or not password:
                        return jsonify({'error': 'Account ID and password are required'}), 400

                    if len(account_id) != 10:
                        return jsonify({'error': 'Account ID must be 10 characters (Taiwanese ID format)'}), 400

                    if password != password_confirm:
                        return jsonify({'error': 'Passwords do not match'}), 400

                    # Save credentials
                    manager.save_credentials(account_id, password)
                    return jsonify({'message': 'Credentials saved successfully'})

                elif request.method == 'DELETE':
                    # Reset credentials
                    manager.reset_credentials()
                    return jsonify({'message': 'Credentials reset successfully'})

            except Exception as e:
                self.logger.error(f"Credentials management error: {e}")
                return jsonify({'error': str(e)}), 500

        @self.app.route('/api/config', methods=['GET', 'POST'])
        def config():
            """Get or update configuration"""
            if request.method == 'GET':
                return jsonify({
                    'autoAnswerQuiz': AUTO_ANSWER_QUIZ,
                    'minQuizScore': MIN_QUIZ_SCORE,
                    'videoCompletionThreshold': VIDEO_COMPLETION_THRESHOLD,
                    'playbackSpeed': PLAYBACK_SPEED,
                    'enableHeadless': ENABLE_HEADLESS
                })
            else:
                # Update config (would need to implement config saving)
                return jsonify({'message': 'Config update not implemented yet'})

    def setup_socket_events(self):
        """Setup SocketIO events"""

        @self.socketio.on('connect')
        def handle_connect():
            emit('status_update', {
                'status': self.current_status,
                'progress': self.progress_info
            })

        @self.socketio.on('disconnect')
        def handle_disconnect():
            pass

    def run_bot(self, courses, max_courses):
        """Run the bot in background thread"""
        self.is_running = True
        self.current_status = "running"

        try:
            # Initialize bot components
            auth_manager = AuthManager()
            if not auth_manager.login():
                self.emit_error("Login failed")
                return

            driver = auth_manager.get_driver()
            navigator = CourseNavigator(driver)

            # Get course list
            self.emit_log("Fetching course list...")
            available_courses = navigator.get_course_list()

            if not available_courses:
                self.emit_error("No courses found")
                return

            # Filter courses
            if courses:
                available_courses = [c for c in available_courses
                                   if any(keyword.lower() in c['title'].lower() for keyword in courses)]

            if max_courses > 0:
                available_courses = available_courses[:max_courses]

            self.progress_info['total_courses'] = len(available_courses)
            self.emit_progress_update()

            # Process courses
            successful_courses = 0
            for i, course in enumerate(available_courses, 1):
                if not self.is_running:
                    break

                self.progress_info['current_course'] = course['title']
                self.emit_progress_update()

                try:
                    self.emit_log(f"Processing course {i}/{len(available_courses)}: {course['title']}")

                    result = navigator.process_course(course)

                    if result.get('final_status', {}).get('completed', False):
                        successful_courses += 1
                        self.emit_log(f"✅ Course completed successfully")
                    else:
                        self.emit_log(f"⚠️  Course not fully completed")

                    self.progress_info['completed_courses'] = i

                except Exception as e:
                    self.emit_log(f"❌ Course processing failed: {e}")

            # Generate report
            self.emit_log(f"Completed {successful_courses}/{len(available_courses)} courses")

        except Exception as e:
            self.emit_error(f"Bot error: {e}")
        finally:
            self.is_running = False
            self.current_status = "idle"
            if 'auth_manager' in locals():
                auth_manager.cleanup()
            self.emit_status_update()

    def emit_log(self, message):
        """Emit log message to web interface"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        log_entry = f"[{timestamp}] {message}"

        self.progress_info['logs'].append(log_entry)
        # Keep only last 50 logs in memory
        if len(self.progress_info['logs']) > 50:
            self.progress_info['logs'] = self.progress_info['logs'][-50:]

        self.socketio.emit('log', {'message': log_entry})

    def emit_progress_update(self):
        """Emit progress update"""
        self.socketio.emit('progress_update', self.progress_info)

    def emit_status_update(self):
        """Emit status update"""
        self.socketio.emit('status_update', {
            'status': self.current_status,
            'is_running': self.is_running,
            'progress': self.progress_info
        })

    def emit_error(self, message):
        """Emit error message"""
        self.current_status = "error"
        self.emit_log(f"❌ {message}")
        self.socketio.emit('error', {'message': message})

    def get_latest_log_file(self):
        """Get the latest log file path"""
        try:
            log_dir = os.path.join(CREDENTIALS_DIR, "logs")
            if not os.path.exists(log_dir):
                return None

            log_files = [f for f in os.listdir(log_dir) if f.startswith('elearning_') and f.endswith('.log')]
            if not log_files:
                return None

            latest_log = max(log_files)
            return os.path.join(log_dir, latest_log)
        except:
            return None

    def run(self, host=WEB_HOST, port=WEB_PORT, debug=WEB_DEBUG):
        """Run the web interface"""
        self.logger.info(f"Starting web interface on http://{host}:{port}")
        self.socketio.run(self.app, host=host, port=port, debug=debug)


# Global web interface instance
web_interface = None

def create_app():
    """Create and return the web interface app"""
    global web_interface
    web_interface = WebInterface()
    return web_interface.app

def run_web_ui():
    """Run the web interface"""
    global web_interface
    if web_interface is None:
        web_interface = WebInterface()
    web_interface.run()


if __name__ == "__main__":
    run_web_ui()