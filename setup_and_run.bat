@echo off
echo ========================================
echo  GRIFFIN - HR Classification Tool Setup
echo  William ^& Mary - Team 7
echo ========================================
echo.

REM Check for conda
where conda >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Conda not found. Please install Miniconda or Anaconda first.
    echo Download: https://docs.conda.io/en/latest/miniconda.html
    pause
    exit /b 1
)

REM Check if griffin env exists
conda env list | findstr "griffin" >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [SETUP] Creating griffin conda environment...
    conda env create -f environment.yml
    if %ERRORLEVEL% neq 0 (
        echo [ERROR] Failed to create conda environment.
        pause
        exit /b 1
    )
) else (
    echo [OK] Griffin environment found.
)

REM Activate
echo [SETUP] Activating griffin environment...
call conda activate griffin

REM Install pip packages that might be missing
echo [SETUP] Ensuring pip packages are installed...
pip install google-generativeai python-dotenv --quiet 2>nul

REM Check for .env
if not exist ".env" (
    if exist ".env.example" (
        copy .env.example .env >nul
        echo.
        echo ========================================
        echo  IMPORTANT: API Key Required
        echo ========================================
        echo  A .env file has been created from .env.example
        echo  You MUST edit .env and add your Google Gemini API key:
        echo    GOOGLE_API_KEY=your-actual-key-here
        echo.
        echo  Without the API key, only Fast Mode (ML) will work.
        echo  Full Analysis mode requires the Gemini API.
        echo ========================================
        echo.
        notepad .env
        pause
    )
) else (
    echo [OK] .env file found.
)

REM Launch
echo.
echo [LAUNCH] Starting GRIFFIN Streamlit app...
echo  The app will open in your browser at http://localhost:8501
echo  Press Ctrl+C in this window to stop the app.
echo.
streamlit run app/streamlit_app.py
