import pandas as pd

df = pd.read_parquet('data/parquet/nanofacs/events/10000 exo and cd81/Exo Control.parquet')
print(f'Shape: {df.shape}')
print(f'Columns: {list(df.columns)[:15]}')
print(f'Has VFSC-H: {"VFSC-H" in df.columns}')
print(f'FSC columns: {[c for c in df.columns if "FSC" in c]}')
