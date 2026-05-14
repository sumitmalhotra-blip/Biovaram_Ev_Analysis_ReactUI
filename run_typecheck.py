#!/usr/bin/env python3
import subprocess
import sys
import os

os.chdir(r'd:\CRM IT Project\Biovaram_Ev_Analysis_ReactUI')
result = subprocess.run(
    ['npx', 'pyright', 'backend/src/api/routers/samples.py'],
    capture_output=False,
    text=True
)
sys.exit(result.returncode)
