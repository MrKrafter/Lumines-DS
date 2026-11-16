@echo off
rem Lumines DS server on Windows: needs Python 3.8+ (python.org, "Add to PATH").
rem Scores are kept next to this file in scores.json. Close the window to stop the server.
cd /d "%~dp0.."
python lumines_server.py --udp 27620 --http 27621 --data scores.json
pause
