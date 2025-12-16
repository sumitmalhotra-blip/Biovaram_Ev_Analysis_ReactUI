"""
Enhanced FCS Parser - Task 1.1
================================

Purpose:
- Parse nanoFACS FCS files with Parquet output
- Extract biological_sample_id and measurement_id from filenames
- Detect baseline vs test measurements
- Calculate statistics and baseline comparisons
- Support AWS S3 storage

Author: CRMIT Team
Date: November 13, 2025
Status: STUB - Implementation pending
"""

import fcsparser
import pandas as pd
import numpy as np
import re
from pathlib import Path
from typing import Dict, Tuple, Optional
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FCSParser:
    """
    Enhanced FCS parser with baseline workflow support and S3 integration.
    """
    
    def __init__(self, config_path: str | None = None):
        """
        Initialize FCS parser with configuration.
        
        Args:
            config_path: Path to configuration file (JSON)
        
        WHAT IT DOES:
        -------------
        Loads parsing rules and configuration settings:
        - Filename patterns for metadata extraction
        - Channel name mappings (different cytometers use different names)
        - Quality control thresholds
        - Output format preferences
        - S3 storage settings (if using cloud)
        
        WHY CONFIGURATION IS EXTERNAL:
        ------------------------------
        - Different labs use different naming conventions
        - Instrument vendors use different channel names
        - Quality thresholds vary by experiment type
        - Easy to update rules without changing code
        
        EXAMPLE CONFIG FILE (config/parser_rules.json):
        -----------------------------------------------
        {
            "filename_patterns": [
                {"pattern": r"L(\d+)\+F(\d+)\+(\w+)",
                 "groups": ["lot", "fraction", "antibody"]},
                {"pattern": r"(\w+)_P(\d+)_(\d+)_(\d+)_(\d+)",
                 "groups": ["experiment", "passage", "day", "month", "year"]}
            ],
            "baseline_keywords": ["ISO", "Isotype", "isotype", "iso", "control"],
            "channel_mappings": {
                "fsc": ["FSC-A", "VFSC-A", "FSC-H", "Forward Scatter"],
                "ssc": ["SSC-A", "VSSC1-A", "SSC-H", "Side Scatter"]
            },
            "qc_thresholds": {
                "min_events": 1000,
                "max_cv_percent": 50,
                "min_median_fsc": 100
            }
        }
        """
        self.config = self._load_config(config_path)
        logger.info("FCS Parser initialized")
    
    def _load_config(self, config_path: str | None) -> Dict:
        """Load parser configuration from JSON file.
        
        IMPLEMENTATION APPROACH:
        ------------------------
        1. If config_path provided:
           - Load JSON file
           - Validate required keys exist
           - Merge with default configuration
        
        2. If config_path is None:
           - Use default configuration (hardcoded)
           - Log warning that defaults are being used
        
        3. Validate configuration:
           - Check filename patterns are valid regex
           - Verify channel mappings are non-empty
           - Ensure thresholds are positive numbers
        
        ERROR HANDLING:
        ---------------
        - FileNotFoundError: Config file doesn't exist → use defaults
        - JSONDecodeError: Invalid JSON → raise error with line number
        - KeyError: Missing required keys → use defaults for that section
        
        EXAMPLE IMPLEMENTATION:
        -----------------------
        import json
        from pathlib import Path
        
        # Default configuration
        default_config = {
            "filename_patterns": [],
            "baseline_keywords": ["ISO", "isotype"],
            "channel_mappings": {"fsc": ["FSC-A"], "ssc": ["SSC-A"]},
            "qc_thresholds": {"min_events": 1000}
        }
        
        if config_path and Path(config_path).exists():
            with open(config_path, 'r') as f:
                config = json.load(f)
            # Merge with defaults
            for key in default_config:
                if key not in config:
                    config[key] = default_config[key]
            return config
        else:
            logger.warning("No config file, using defaults")
            return default_config
        
        TODO: Implement config loading
        """
        # TODO: Implement config loading
        return {}
    
    def parse_filename(self, filename: str) -> Dict[str, str]:
        """
        Extract metadata from FCS filename using pattern matching.
        
        Args:
            filename: FCS filename (e.g., "L5+F10+CD81.fcs")
        
        Returns:
            Dictionary with:
                - biological_sample_id: Unique ID for biological sample (e.g., "P5_F10")
                - measurement_id: Unique ID for this measurement (includes antibody)
                - antibody: Antibody used (CD81, CD9, CD63, ISO)
                - concentration: Antibody concentration if specified (e.g., "0.25ug")
                - method: Purification method (SEC, Centri, etc.)
                - is_baseline: Boolean, true if isotype control
        
        FILENAME PATTERNS:
        ------------------
        Your lab uses several naming conventions:
        
        Pattern 1: "L{lot}+F{fraction}+{antibody}.fcs"
        Example: "L5+F10+CD81.fcs"
        Extract: lot=5, fraction=10, antibody=CD81
        biological_sample_id = "L5_F10"
        
        Pattern 2: "{amount}ug {antibody} {method}.fcs"
        Example: "0.25ug CD81 SEC.fcs"
        Extract: amount=0.25, antibody=CD81, method=SEC
        
        Pattern 3: "EV_IPSC_P{passage}_{date}_NTA"
        Example: "EV_IPSC_P2_27_2_25_NTA"
        Extract: passage=2, date=27/2/25
        biological_sample_id = "IPSC_P2"
        
        Pattern 4: "Exo+ {amount}ug {antibody} {method}.fcs"
        Example: "Exo+ 1ug CD81 Centri.fcs"
        Extract: amount=1, antibody=CD81, method=Centri
        
        BASELINE DETECTION:
        -------------------
        Baselines (isotype controls) have keywords:
        - "ISO", "Isotype", "isotype", "iso"
        - "control", "Control"
        
        Examples:
        - "L5+F10+ISO.fcs" → is_baseline=True
        - "0.25ug ISO SEC.fcs" → is_baseline=True
        - "L5+F10+CD81.fcs" → is_baseline=False
        
        IMPLEMENTATION APPROACH:
        ------------------------
        1. Try each regex pattern in order
        2. When match found, extract named groups
        3. Construct biological_sample_id from lot+fraction or passage
        4. Construct measurement_id by appending antibody
        5. Check for baseline keywords
        6. Return structured metadata dictionary
        
        REGEX EXAMPLES:
        ---------------
        import re
        
        # Pattern for "L5+F10+CD81.fcs"
        pattern1 = r'L(?P<lot>\d+)\+F(?P<fraction>\d+)\+(?P<antibody>\w+)\.fcs'
        match = re.match(pattern1, filename)
        if match:
            lot = match.group('lot')         # "5"
            fraction = match.group('fraction') # "10"
            antibody = match.group('antibody') # "CD81"
            bio_id = f"L{lot}_F{fraction}"  # "L5_F10"
            meas_id = f"{bio_id}_{antibody}" # "L5_F10_CD81"
        
        # Pattern for "0.25ug CD81 SEC.fcs"
        pattern2 = r'(?P<amount>[\d.]+)ug (?P<antibody>\w+) (?P<method>\w+)\.fcs'
        
        # Pattern for "Exo+ 1ug CD81 Centri.fcs"
        pattern3 = r'Exo\+ (?P<amount>[\d.]+)ug (?P<antibody>\w+) (?P<method>\w+)\.fcs'
        
        ERROR HANDLING:
        ---------------
        - If no pattern matches: Generate generic IDs from filename
        - If missing fields: Use "Unknown" as placeholder
        - Log warning for unparseable filenames
        
        EXAMPLE OUTPUT:
        ---------------
        Input: "L5+F10+CD81.fcs"
        Output: {
            'biological_sample_id': 'L5_F10',
            'measurement_id': 'L5_F10_CD81',
            'antibody': 'CD81',
            'concentration': None,
            'method': None,
            'is_baseline': False,
            'filename': 'L5+F10+CD81.fcs'
        }
        
        Input: "0.25ug ISO SEC.fcs"
        Output: {
            'biological_sample_id': 'Unknown_ISO_SEC',
            'measurement_id': 'Unknown_ISO_SEC_025ug',
            'antibody': 'ISO',
            'concentration': '0.25ug',
            'method': 'SEC',
            'is_baseline': True,
            'filename': '0.25ug ISO SEC.fcs'
        }
        
        TODO: Implement filename parsing logic based on patterns
        """
        raise NotImplementedError("Filename parsing not yet implemented")
    
    def parse_fcs_file(self, fcs_path: str) -> Tuple[pd.DataFrame, Dict]:
        """
        Parse single FCS file and extract events + metadata.
        
        Args:
            fcs_path: Path to FCS file (local or S3)
        
        Returns:
            Tuple of (events_df, metadata_dict)
        
        WHAT IT DOES:
        -------------
        1. Read FCS binary file (handles FCS 2.0, 3.0, 3.1 formats)
        2. Extract TEXT segment (metadata like $P1N, $P2N channel names)
        3. Extract DATA segment (event data - FSC, SSC, fluorescence)
        4. Convert to pandas DataFrame with channel names as columns
        5. Extract acquisition metadata (date, time, cytometer settings)
        6. Parse filename to get biological sample IDs
        7. Return both event data and metadata
        
        FCS FILE STRUCTURE:
        -------------------
        FCS files have 6 segments:
        1. HEADER (58 bytes): Version, segment offsets
        2. TEXT: Key-value pairs with $KEY format
           - $P1N: "FSC-A" (parameter 1 name)
           - $P2N: "SSC-A" (parameter 2 name)
           - $TOT: "50000" (total events)
           - $DATE: "19-Nov-2025"
        3. DATA: Binary event data (int or float)
        4. ANALYSIS (optional): Gating, statistics
        5. SUPPLEMENT (optional): Additional data
        6. OTHER (optional): Custom data
        
        MEMORY EFFICIENCY - CHUNKED PROCESSING:
        ---------------------------------------
        For large files (>100MB, >1M events), load in chunks:
        
        Instead of:
          df = load_all_events()  # 1GB RAM for 10M events
        
        Do:
          for chunk in load_events_chunked(chunk_size=50000):
              process(chunk)      # Only 50MB RAM at a time
              save_chunk(chunk)
        
        Benefits:
        - Process files larger than available RAM
        - Faster time to first result (don't wait for full load)
        - Can filter/downsample during load (save memory)
        
        CHANNEL NAME STANDARDIZATION:
        -----------------------------
        Different cytometers use different naming:
        - BD: "FSC-A", "SSC-A"
        - Bio-Rad ZE5: "VFSC-A", "VSSC1-A"
        - Cytek: "FSC", "SSC"
        
        This parser normalizes to standard names:
        "VFSC-A" → "FSC-A"
        "VSSC1-A" → "SSC-A"
        
        COMPENSATION:
        -------------
        Fluorescence spillover correction (optional):
        - If $SPILL matrix exists in metadata: Apply compensation
        - Otherwise: Use raw data
        
        Compensation corrects for:
        - FITC signal bleeding into PE channel
        - PE signal bleeding into PE-Cy7 channel
        
        ERROR HANDLING:
        ---------------
        - FCS format errors: Invalid header, wrong version
        - Data errors: Missing channels, corrupt binary data
        - Memory errors: File too large for available RAM
        - IO errors: File not found, permission denied, S3 timeout
        
        IMPLEMENTATION EXAMPLE:
        -----------------------
        import fcsparser
        
        try:
            # Parse FCS file using fcsparser library
            meta, data = fcsparser.parse(
                fcs_path,
                meta_data_only=False,    # Load event data, not just metadata
                compensate=False,        # Don't apply compensation (do manually)
                channel_naming='$PnN'    # Use short names (FSC-A, not "Forward Scatter")
            )
            
            # Extract key metadata
            metadata = {
                'total_events': int(meta.get('$TOT', 0)),
                'acquisition_date': meta.get('$DATE', 'Unknown'),
                'acquisition_time': meta.get('$BTIM', 'Unknown'),
                'cytometer': meta.get('$CYT', 'Unknown'),
                'channels': list(data.columns)
            }
            
            # Parse filename for sample IDs
            filename_meta = self.parse_filename(Path(fcs_path).name)
            metadata.update(filename_meta)
            
            # Convert to DataFrame (already is, but standardize)
            events_df = pd.DataFrame(data)
            
            logger.info(f"Parsed {len(events_df):,} events, {len(events_df.columns)} channels")
            
            return events_df, metadata
            
        except Exception as e:
            logger.error(f"Failed to parse FCS file {fcs_path}: {e}")
            raise
        
        TODO: Implement FCS parsing with chunking for memory efficiency
        """
        raise NotImplementedError("FCS parsing not yet implemented")
    
    def calculate_statistics(self, events: pd.DataFrame) -> Dict:
        """
        Calculate pre-computed statistics for all parameters.
        
        Args:
            events: DataFrame with event data (rows=events, columns=channels)
        
        Returns:
            Dictionary with mean, median, std, etc. for all 26 parameters
        
        WHY PRE-CALCULATE STATISTICS:
        -----------------------------
        Instead of loading 10M events every time you need a median:
        - Pre-calculate during parsing (one-time cost)
        - Store in metadata file (KB instead of GB)
        - Instant access to summary statistics
        
        Example:
        Without pre-calculation:
          1. Load 1GB Parquet file
          2. Calculate median FSC
          3. Takes 5 seconds
        
        With pre-calculation:
          1. Read from metadata JSON
          2. Get median FSC
          3. Takes 0.001 seconds (5000× faster)
        
        STATISTICS TO CALCULATE:
        ------------------------
        For each channel (FSC-A, SSC-A, etc.):
        - count: Number of valid (non-NaN) events
        - mean: Average value
        - median: 50th percentile (robust to outliers)
        - std: Standard deviation (spread)
        - min: Minimum value
        - max: Maximum value
        - p5, p25, p75, p95: Percentiles for distribution shape
        - cv: Coefficient of variation (std/mean × 100%)
        
        COEFFICIENT OF VARIATION (CV):
        ------------------------------
        CV = (std / mean) × 100%
        
        Interpretation:
        - CV < 10%: Very uniform (calibration beads)
        - CV 10-30%: Normal biological variation (EVs)
        - CV > 50%: High variation (multiple populations or artifacts)
        
        Used for quality control:
        - Flag samples with high CV (check for doublets, debris)
        - Compare CV across replicates (consistency check)
        
        IMPLEMENTATION APPROACH:
        ------------------------
        import numpy as np
        
        stats = {}
        
        for channel in events.columns:
            values = events[channel].values
            
            # Remove NaN and infinite values
            valid = values[np.isfinite(values)]
            
            if len(valid) == 0:
                # No valid data - all NaN
                stats[channel] = {'count': 0, 'mean': np.nan}
                continue
            
            # Calculate statistics
            stats[channel] = {
                'count': len(valid),
                'mean': np.mean(valid),
                'median': np.median(valid),
                'std': np.std(valid),
                'min': np.min(valid),
                'max': np.max(valid),
                'p5': np.percentile(valid, 5),
                'p25': np.percentile(valid, 25),
                'p75': np.percentile(valid, 75),
                'p95': np.percentile(valid, 95),
                'cv': (np.std(valid) / np.mean(valid) * 100) if np.mean(valid) > 0 else np.nan
            }
        
        return stats
        
        EXAMPLE OUTPUT:
        ---------------
        {
            'FSC-A': {
                'count': 50000,
                'mean': 12543.2,
                'median': 11234.5,
                'std': 3421.1,
                'min': 100.0,
                'max': 65535.0,
                'p5': 5234.1,
                'p95': 23451.2,
                'cv': 27.3  # 27.3% variation
            },
            'SSC-A': {...},
            'FITC-A': {...}
        }
        
        TODO: Implement statistics calculation
        """
        raise NotImplementedError("Statistics calculation not yet implemented")
    
    def detect_baseline(self, metadata: Dict) -> bool:
        """
        Detect if measurement is a baseline (isotype control).
        
        Args:
            metadata: Sample metadata (from parse_filename or FCS TEXT)
        
        Returns:
            True if baseline, False if test
        
        WHAT ARE BASELINES (ISOTYPE CONTROLS):
        --------------------------------------
        In flow cytometry experiments:
        - Test samples: Specific antibody (CD81, CD9, CD63)
          Binds to EV surface markers
        
        - Baseline/Control samples: Isotype control antibody (ISO)
          Same species/class as test, but no specific binding
          Measures background/non-specific binding
        
        Analysis workflow:
        1. Measure baseline with ISO → get background signal
        2. Measure test with CD81 → get total signal
        3. Calculate: specific_signal = total - background
        4. Fold change: total / background
        
        DETECTION METHODS:
        ------------------
        Check multiple locations for baseline keywords:
        
        1. Filename:
           "L5+F10+ISO.fcs" → contains "ISO" → is_baseline=True
           "0.25ug isotype SEC.fcs" → contains "isotype" → True
        
        2. Antibody field (from parse_filename):
           metadata['antibody'] == 'ISO' → True
           metadata['antibody'] == 'CD81' → False
        
        3. FCS metadata (if present):
           $SAMPLE_NAME: "Isotype Control" → True
           $EXPERIMENT: "ISO baseline" → True
        
        BASELINE KEYWORDS:
        ------------------
        Case-insensitive matching:
        - "ISO", "iso", "Iso"
        - "Isotype", "isotype", "ISOTYPE"
        - "Control", "control"
        - "Baseline", "baseline"
        - "IgG" (isotype antibody class)
        
        IMPLEMENTATION EXAMPLE:
        -----------------------
        # Keywords to check (case-insensitive)
        baseline_keywords = ['iso', 'isotype', 'control', 'baseline', 'igg']
        
        # Check filename
        filename = metadata.get('filename', '').lower()
        if any(keyword in filename for keyword in baseline_keywords):
            return True
        
        # Check antibody field
        antibody = metadata.get('antibody', '').lower()
        if any(keyword in antibody for keyword in baseline_keywords):
            return True
        
        # Check sample name from FCS
        sample_name = metadata.get('sample_name', '').lower()
        if any(keyword in sample_name for keyword in baseline_keywords):
            return True
        
        # Not a baseline
        return False
        
        EXAMPLE USAGE:
        --------------
        metadata = {
            'filename': 'L5+F10+CD81.fcs',
            'antibody': 'CD81'
        }
        is_baseline = detect_baseline(metadata)  # False
        
        metadata = {
            'filename': '0.25ug ISO SEC.fcs',
            'antibody': 'ISO'
        }
        is_baseline = detect_baseline(metadata)  # True
        
        TODO: Check for "ISO", "Isotype", "isotype", "iso" in filename/metadata
        """
        raise NotImplementedError("Baseline detection not yet implemented")
    
    def save_to_parquet(self, data: pd.DataFrame, output_path: str):
        """
        Save DataFrame to Parquet with Snappy compression.
        
        Args:
            data: DataFrame to save
            output_path: Output path (local or S3)
        
        WHY PARQUET INSTEAD OF CSV:
        ---------------------------
        Comparison for 1M events, 26 channels:
        
        Format    Size     Read Time   Write Time   Type Safety
        -------   -----    ---------   ----------   -----------
        FCS       10.5 MB  2.3 sec     N/A          Yes (binary)
        CSV       25.3 MB  8.5 sec     4.2 sec      No (all strings)
        Parquet   1.2 MB   0.4 sec     1.1 sec      Yes (schema)
        
        Parquet advantages:
        1. 88% smaller than FCS (90% with Gzip)
        2. 5× faster to read than CSV
        3. Columnar format: Read only needed columns
        4. Built-in compression (Snappy, Gzip, Brotli)
        5. Preserves dtypes (int64, float64, datetime)
        6. Works with big data tools (Spark, Dask, Athena)
        
        COMPRESSION OPTIONS:
        --------------------
        1. Snappy (default):
           - Fast compression (200 MB/s)
           - Fast decompression (500 MB/s)
           - Good ratio (2-4×)
           - Best for: Frequent access, iterative analysis
        
        2. Gzip:
           - Slower compression (50 MB/s)
           - Slower decompression (100 MB/s)
           - Better ratio (5-10×)
           - Best for: Archive storage, reduce S3 costs
        
        3. None (uncompressed):
           - Fastest read/write
           - Largest files
           - Best for: Temporary files, SSD storage
        
        PARQUET FILE STRUCTURE:
        -----------------------
        Parquet files are columnar, not row-based:
        
        Row format (CSV, FCS):
          Event1: FSC=100, SSC=200, FITC=50
          Event2: FSC=105, SSC=210, FITC=48
          ...
          (Good for reading entire rows)
        
        Column format (Parquet):
          FSC: [100, 105, 108, ...]
          SSC: [200, 210, 205, ...]
          FITC: [50, 48, 52, ...]
          (Good for reading specific columns)
        
        Benefits:
        - Query: SELECT median(FSC) → Read only FSC column
        - Better compression (similar values together)
        - Vectorized operations (SIMD processing)
        
        SCHEMA (DATA TYPES):
        --------------------
        Parquet stores schema (column types):
        {
            'FSC-A': int32,
            'SSC-A': int32,
            'FITC-A': float32,
            'timestamp': datetime64,
            'sample_id': string
        }
        
        Benefits:
        - No type inference on read (faster)
        - Prevents type errors (can't add string to int)
        - More efficient storage (int32 = 4 bytes vs string = 10+ bytes)
        
        METADATA:
        ---------
        Parquet can store custom metadata:
        - Original FCS filename
        - Acquisition date/time
        - Cytometer model
        - Processing history
        - Quality metrics
        
        Access metadata:
        import pyarrow.parquet as pq
        pf = pq.read_metadata('file.parquet')
        custom_meta = pf.metadata[b'sample_id'].decode()
        
        S3 SUPPORT:
        -----------
        Parquet works seamlessly with S3:
        
        # Local
        df.to_parquet('local/path/file.parquet')
        
        # S3 (using s3fs or boto3)
        df.to_parquet('s3://bucket/path/file.parquet')
        
        # Read specific columns from S3 (no download)
        df = pd.read_parquet(
            's3://bucket/file.parquet',
            columns=['FSC-A', 'SSC-A']  # Only read these
        )
        
        IMPLEMENTATION EXAMPLE:
        -----------------------
        from pathlib import Path
        import pandas as pd
        
        try:
            # Ensure output directory exists
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            
            # Save with compression
            data.to_parquet(
                output_path,
                engine='pyarrow',      # Fast engine (vs 'fastparquet')
                compression='snappy',  # Fast compression
                index=False,           # Don't save DataFrame index
                # Optional: Add custom metadata
                # custom_metadata={
                #     'sample_id': metadata['biological_sample_id'],
                #     'acquisition_date': metadata['date']
                # }
            )
            
            # Get file size
            file_size = Path(output_path).stat().st_size
            logger.info(f"✅ Saved {len(data):,} events to {output_path}")
            logger.info(f"   File size: {file_size/1e6:.2f} MB")
            
        except Exception as e:
            logger.error(f"Failed to save Parquet: {e}")
            raise
        
        TODO: Implement Parquet save with S3 support
        """
        raise NotImplementedError("Parquet save not yet implemented")


def main():
    """Main entry point for FCS parser."""
    logger.info("FCS Parser - Implementation pending")
    logger.info("See TASK_TRACKER.md Task 1.1 for requirements")


if __name__ == "__main__":
    main()
