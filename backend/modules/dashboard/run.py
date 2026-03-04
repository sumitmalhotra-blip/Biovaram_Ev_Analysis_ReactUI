"""
BioVaram Dashboard Module — Desktop Entry Point
=================================================
Launch: python -m modules.dashboard.run
"""
from modules.run_module import run_module

if __name__ == "__main__":
    run_module(
        module_name="dashboard",
        module_title="Dashboard",
    )
