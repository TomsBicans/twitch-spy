@echo off

REM Check if virtual environment exists
if not exist venv (
    REM Try to create virtual environment with 'py'
    py -m venv venv
    if errorlevel 1 (
        REM If 'py' fails, try 'python3'
        python3 -m venv venv
        if errorlevel 1 (
            echo Could not create virtual environment.
            exit /b
        )
    )
)

call venv\Scripts\activate

REM Use the activated environment's pip
pip install -r requirements.txt
if errorlevel 1 (
    echo Could not install requirements.
    exit /b
)
