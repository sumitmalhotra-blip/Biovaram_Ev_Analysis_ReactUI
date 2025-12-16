"""
Utility class for writing DataFrames to Parquet with metadata.
"""

from pathlib import Path
from typing import Dict, Any, Optional
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from loguru import logger


class ParquetWriter:
    """Utility class for writing DataFrames to Parquet format with metadata."""
    
    @staticmethod
    def write(
        data: pd.DataFrame,
        output_path: Path,
        metadata: Optional[Dict[str, Any]] = None,
        compression: str = 'snappy',
        partition_cols: Optional[list] = None
    ) -> None:
        """
        Write DataFrame to Parquet file with optional metadata.
        
        Args:
            data: DataFrame to write
            output_path: Output file path
            metadata: Dictionary of metadata to embed
            compression: Compression codec ('snappy', 'gzip', 'zstd', 'none')
            partition_cols: Columns to partition by (for dataset writing)
        """
        try:
            # Create output directory if needed
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Convert DataFrame to Arrow Table
            table = pa.Table.from_pandas(data)
            
            # Add metadata if provided
            if metadata:
                metadata_bytes = {
                    k.encode(): str(v).encode() 
                    for k, v in metadata.items()
                }
                schema = table.schema.with_metadata(metadata_bytes)
                table = table.cast(schema)
            
            # Write to Parquet
            pq.write_table(
                table,
                output_path,
                compression=compression,
                use_dictionary=True,
                write_statistics=True,
                version='2.6'  # Latest Parquet format
            )
            
            file_size_mb = output_path.stat().st_size / (1024 * 1024)
            logger.info(f"Γ£ô Wrote Parquet: {output_path.name} ({file_size_mb:.2f} MB)")
            
        except Exception as e:
            logger.error(f"Failed to write Parquet file: {e}")
            raise
    
    @staticmethod
    def read_with_metadata(parquet_path: Path) -> tuple:
        """
        Read Parquet file and extract embedded metadata.
        
        Args:
            parquet_path: Path to Parquet file
            
        Returns:
            Tuple of (DataFrame, metadata_dict)
        """
        try:
            # Read Parquet file
            table = pq.read_table(parquet_path)
            
            # Extract metadata
            metadata = {}
            if table.schema.metadata:
                metadata = {
                    k.decode(): v.decode() 
                    for k, v in table.schema.metadata.items()
                }
            
            # Convert to DataFrame
            df = table.to_pandas()
            
            logger.info(f"Γ£ô Read Parquet: {parquet_path.name}")
            return df, metadata
            
        except Exception as e:
            logger.error(f"Failed to read Parquet file: {e}")
            raise
    
    @staticmethod
    def get_file_info(parquet_path: Path) -> Dict[str, Any]:
        """
        Get information about Parquet file without loading data.
        
        Args:
            parquet_path: Path to Parquet file
            
        Returns:
            Dictionary with file information
        """
        try:
            parquet_file = pq.ParquetFile(parquet_path)
            
            info = {
                'num_rows': parquet_file.metadata.num_rows,
                'num_columns': parquet_file.metadata.num_columns,
                'num_row_groups': parquet_file.metadata.num_row_groups,
                'format_version': parquet_file.metadata.format_version,
                'created_by': parquet_file.metadata.created_by,
                'serialized_size': parquet_file.metadata.serialized_size,
            }
            
            # Get column names and types
            info['columns'] = [
                {
                    'name': field.name,
                    'type': str(field.type)
                }
                for field in parquet_file.schema_arrow
            ]
            
            # Get compression info from first row group
            if parquet_file.metadata.num_row_groups > 0:
                rg = parquet_file.metadata.row_group(0)
                compressions = set()
                for i in range(rg.num_columns):
                    col = rg.column(i)
                    compressions.add(col.compression)
                info['compression'] = list(compressions)
            
            return info
            
        except Exception as e:
            logger.error(f"Failed to get Parquet info: {e}")
            raise
