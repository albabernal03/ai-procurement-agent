@echo off
REM Activa el entorno y lanza la API
call .venv\Scripts\activate
uvicorn main:app --reload --port 8000
