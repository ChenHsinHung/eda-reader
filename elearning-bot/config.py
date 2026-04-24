"""
Configuration file for elearning-bot
Account credentials are stored separately in encrypted files.
To change credentials, run: python setup.py --reset
"""

import os

# Course selection
COURSES_TO_COMPLETE = []  # Empty list means all courses
# Example: ["課程名稱1", "課程名稱2"]

# Quiz configuration
AUTO_ANSWER_QUIZ = True          # Whether to auto-answer quizzes
QUIZ_METHOD = "traditional"      # "traditional" (trial-and-error) or "ai" (use AI)
MIN_QUIZ_SCORE = 60              # Minimum passing score
ALLOW_QUIZ_RETRY = True          # Whether to retry if score is below minimum

# AI configuration (if QUIZ_METHOD == "ai")
AI_PROVIDER = None               # "openai" / "claude" / "google" or None
AI_API_KEY = None                # API key (use environment variables for security)

# Video player configuration
PLAYBACK_SPEED = 1.0             # Playback speed (1.0 = normal)
VIDEO_TIMEOUT = 1800             # Single video timeout in seconds
VIDEO_COMPLETION_THRESHOLD = 0.9 # Video completion threshold (90%)
ENABLE_HEADLESS = True           # Headless mode (background running)

# Platform-specific configuration
import platform
if platform.system() == "Windows":
    CREDENTIALS_DIR = os.path.expandvars(r"%LOCALAPPDATA%\elearning-bot")
    TESSERACT_PATH = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
elif platform.system() == "Darwin":  # macOS
    CREDENTIALS_DIR = os.path.expanduser("~/Library/Application Support/elearning-bot")
    TESSERACT_PATH = "/usr/local/bin/tesseract"  # or "/opt/homebrew/bin/tesseract"
else:  # Linux and others
    CREDENTIALS_DIR = os.path.expanduser("~/.config/elearning-bot")
    TESSERACT_PATH = "/usr/bin/tesseract"

# Web interface configuration
ENABLE_WEB_UI = True           # Enable web interface
WEB_HOST = "127.0.0.1"         # Web server host
WEB_PORT = 8080                # Web server port
WEB_DEBUG = False              # Flask debug mode
WEB_SECRET_KEY = "elearning-bot-secret-key"  # Flask secret key

# Logging configuration
LOG_LEVEL = "INFO"               # DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_MAX_SIZE = 10 * 1024 * 1024  # 10MB per log file
LOG_BACKUP_COUNT = 5             # Keep 5 backup log files

# Network configuration
REQUEST_TIMEOUT = 30             # HTTP request timeout in seconds
RETRY_ATTEMPTS = 3               # Number of retry attempts
RETRY_DELAY = 5                  # Initial retry delay in seconds

# Browser configuration
BROWSER_WAIT_TIMEOUT = 30        # Selenium wait timeout in seconds
BROWSER_IMPLICIT_WAIT = 10       # Implicit wait time in seconds