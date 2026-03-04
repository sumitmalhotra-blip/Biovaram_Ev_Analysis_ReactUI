"""
BioVaram Cross-Compare Module — Desktop Entry Point
=====================================================
Launch: python -m modules.cross_compare.run
"""
from modules.run_module import run_module

if __name__ == "__main__":
    run_module(
        module_name="cross_compare",
        module_title="Cross-Compare Analysis",
    )
