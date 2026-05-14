@echo off
cd /d "d:\CRM IT Project\Biovaram_Ev_Analysis_ReactUI"
echo === Running ESLint ===
call npm run lint
echo.
echo === Running Next.js Build ===
call npm run build
