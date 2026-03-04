"""
BioVaram NanoFACS Module — Desktop Entry Point
================================================
Launch: python -m modules.nanofacs.run
"""
from modules.run_module import run_module

if __name__ == "__main__":
    run_module(
        module_name="nanofacs",
        module_title="NanoFACS Analysis",
    )
