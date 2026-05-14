@echo off
REM Simple validation batch script - does not require PowerShell 7+
cd /d "d:\CRM IT Project\Biovaram_Ev_Analysis_ReactUI"

echo Validating NanoFACS AI Implementation...
echo.

REM Run Python validation
python IMPLEMENTATION_VALIDATION.py

if %ERRORLEVEL% EQU 0 (
    echo.
    echo All validations passed!
    exit /b 0
) else (
    echo.
    echo Some validations failed. Review above.
    exit /b 1
)
