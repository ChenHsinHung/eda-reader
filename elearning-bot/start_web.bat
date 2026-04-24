@echo off
cd /d "%~dp0"
if not exist venv (
    echo Creating virtual environment...
    python -m venv venv
)
call venv\Scripts\activate.bat
if not exist venv\Lib\site-packages\PIL (
    echo Installing dependencies...
    pip install -r requirements.txt
)
echo Starting eLearning Bot Web Interface...
echo Open your browser to: http://127.0.0.1:8080
python main.py --web
pause