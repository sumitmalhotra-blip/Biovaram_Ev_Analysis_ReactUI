"""
BioVaram Full Platform — Desktop Entry Point
==============================================
Launch: python -m modules.full_platform.run

This is equivalent to run_desktop.py but uses the modular architecture.
"""
from modules.run_module import run_module

if __name__ == "__main__":
    run_module(
        module_name="full_platform",
        module_title="EV Analysis Platform",
    )
