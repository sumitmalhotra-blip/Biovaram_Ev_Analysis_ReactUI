"""Extract FCS metadata"""
import sys
sys.path.insert(0, '.')
from pathlib import Path
from src.parsers.fcs_parser import FCSParser

fcs_path = Path('nanoFACS/Exp_20251217_PC3/PC3 EXO1.fcs')
parser = FCSParser(fcs_path)
parser.parse()
metadata = parser.extract_metadata()

print('='*60)
print('FCS FILE METADATA')
print('='*60)
print(f'File: {fcs_path.name}')
print(f'Size: {fcs_path.stat().st_size / (1024*1024):.2f} MB')
print()
print('--- ACQUISITION ---')
print(f'Date: {metadata.get("acquisition_date", "Unknown")}')
print(f'Time: {metadata.get("acquisition_time", "Unknown")}')
print(f'Cytometer: {metadata.get("cytometer", "Unknown")}')
print(f'Operator: {metadata.get("operator", "Unknown")}')
print(f'Specimen: {metadata.get("specimen", "Unknown")}')
print()
print('--- DATA SUMMARY ---')
print(f'Total Events: {metadata.get("total_events", 0):,}')
print(f'Parameters: {metadata.get("parameters", 0)}')
print(f'Channel Count: {metadata.get("channel_count", 0)}')
print()
print('--- IDENTIFIERS ---')
print(f'Sample ID: {metadata.get("sample_id")}')
print(f'Biological Sample ID: {metadata.get("biological_sample_id")}')
print(f'Measurement ID: {metadata.get("measurement_id")}')
print(f'Is Baseline: {metadata.get("is_baseline", False)}')
print()
print('--- CHANNELS (26) ---')
for i, ch in enumerate(metadata.get('channel_names', []), 1):
    print(f'  {i:2}. {ch}')
