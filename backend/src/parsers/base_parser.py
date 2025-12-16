"""
Base parser class for all instrument data parsers.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any, Optional
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from loguru import logger


class BaseParser(ABC):
    """Abstract base class for all data parsers."""
    
    def __init__(self, file_path: Path):
        """
        Initialize parser.
        
        Args:
            file_path: Path to file to parse
        """
        self.file_path = Path(file_path)
        self.metadata: Dict[str, Any] = {}
        self.data: Optional[pd.DataFrame] = None
        
    @abstractmethod
    def parse(self) -> pd.DataFrame:
        """
        Parse the file and return DataFrame.
        
        Returns:
            Parsed data as DataFrame
        """
        pass
    
    @abstractmethod
    def extract_metadata(self) -> Dict[str, Any]:
        """
        Extract metadata from file.
        
        Returns:
            Dictionary of metadata
        """
        pass
    
    @abstractmethod
    def validate(self) -> bool:
        """
        Validate file integrity.
        
        Returns:
            True if file is valid, False otherwise
        """
        pass
    
    def to_parquet(
        self, 
        output_path: Path, 
        compression: str = 'snappy',
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Convert parsed data to Parquet format with embedded metadata.
        
        Args:
            output_path: Path for output Parquet file
            compression: Compression codec (snappy, gzip, zstd, none)
            metadata: Additional metadata to embed in Parquet file
        
        HOW IT WORKS:
        -------------
        1. Validate data exists (must call parse() first)
        2. Create output directory if needed
        3. Convert pandas DataFrame to PyArrow Table
        4. Embed metadata in Parquet file header
        5. Write with compression and optimizations
        6. Log file size for monitoring
        
        WHY PYARROW TABLE:
        ------------------
        Pandas -> PyArrow -> Parquet ensures:
        - Correct data type mapping (int64 stays int64, not string)
        - Efficient columnar storage
        - Fast writes (multi-threaded)
        - Proper null handling (NaN -> null)
        """
        # Step 1: Validate that data has been parsed
        # -------------------------------------------
        # If parse() hasn't been called yet, self.data will be None
        if self.data is None:
            raise ValueError("No data to convert. Call parse() first.")
        
        # Step 2: Create output directory if it doesn't exist
        # ----------------------------------------------------
        # mkdir with parents=True creates all parent directories
        # exist_ok=True means no error if directory already exists
        # Example: output_path = "data/parquet/events/sample1.parquet"
        #          Creates: data/, data/parquet/, data/parquet/events/
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Step 3: Convert pandas DataFrame to Apache Arrow Table
        # -------------------------------------------------------
        # Arrow is columnar in-memory format (like Parquet but uncompressed)
        # Benefits of Arrow intermediate step:
        # - Type safety: pandas int64 -> Arrow int64 -> Parquet INT64
        # - Memory efficiency: Zero-copy when possible
        # - Fast conversion: Native C++ implementation
        table = pa.Table.from_pandas(self.data)
        
        # Step 4: Prepare metadata to embed in Parquet file
        # --------------------------------------------------
        # Parquet files can store custom key-value metadata in the header
        # This is separate from the data itself (doesn't affect queries)
        # Useful for: provenance, processing history, quality metrics
        metadata_dict = {
            'source_file': str(self.file_path),     # Original FCS filename
            'parser_version': '1.0.0',              # Track parser version
            **self.metadata                          # Include all parsed metadata
        }
        
        # Add any additional metadata passed by caller
        # Example: {'qc_passed': 'True', 'analyst': 'John'}
        if metadata:
            metadata_dict.update(metadata)
        
        # Step 5: Convert metadata to bytes (Parquet requirement)
        # --------------------------------------------------------
        # Parquet metadata must be bytes, not strings
        # Convert: {'key': 'value'} -> {b'key': b'value'}
        metadata_bytes = {
            k.encode(): str(v).encode() 
            for k, v in metadata_dict.items()
        }
        
        # Step 6: Attach metadata to Arrow Table schema
        # ----------------------------------------------
        # Schema defines column names, types, and file-level metadata
        # Create new schema with our custom metadata attached
        schema = table.schema.with_metadata(metadata_bytes)
        table = table.cast(schema)  # Apply new schema to table
        
        # Step 7: Write to Parquet file with optimizations
        # -------------------------------------------------
        pq.write_table(
            table, 
            output_path, 
            compression=compression,       # Compress data (snappy=fast, gzip=small)
            use_dictionary=True,           # Encode repeated values once (saves space)
            write_statistics=True,         # Min/max per column (faster queries)
            version='2.6'                  # Latest Parquet format (best features)
        )
        # Dictionary encoding example:
        # Instead of: ["CD81", "CD81", "CD81", ...] (10MB)
        # Store as: [0, 0, 0, ...] + dictionary: {0: "CD81"} (1MB)
        
        # Statistics example:
        # Store: column_FSC_min=100, column_FSC_max=50000
        # Query: SELECT * WHERE FSC > 60000 → Skip file instantly (no read)
        
        # Step 8: Log file size for monitoring
        # -------------------------------------
        # Get file size in MB to track compression ratio
        file_size_mb = output_path.stat().st_size / (1024 * 1024)
        logger.info(f"Saved Parquet file: {output_path} ({file_size_mb:.2f} MB)")
    
    def get_file_info(self) -> Dict[str, Any]:
        """
        Get basic file information.
        
        Returns:
            Dictionary with file info
        """
        return {
            'file_name': self.file_path.name,
            'file_path': str(self.file_path),
            'file_size_mb': self.file_path.stat().st_size / (1024 * 1024),
            'exists': self.file_path.exists(),
        }
