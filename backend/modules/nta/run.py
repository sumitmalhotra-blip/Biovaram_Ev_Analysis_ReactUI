"""
BioVaram NTA Module — Desktop Entry Point
==========================================
Launch: python -m modules.nta.run
"""
from modules.run_module import run_module

if __name__ == "__main__":
    run_module(
        module_name="nta",
        module_title="NTA Analysis",
    )
