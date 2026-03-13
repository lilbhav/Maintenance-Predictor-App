@echo off
REM Sets the Anaconda Library bin path so _sqlite3 DLL is found, then starts uvicorn.
SET "PATH=C:\Users\chavab\anaconda3\Library\bin;%PATH%"
cd /d "%~dp0"
call .venv\Scripts\activate.bat
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
