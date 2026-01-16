"""
FCS (Flow Cytometry Standard) file parser.
Supports FCS 2.0, 3.0, and 3.1 formats with memory-efficient chunked processing.
"""

from pathlib import Path
from typing import Dict, Any, List, Optional, Union
import pandas as pd
import numpy as np
try:
    import fcsparser
    USE_FCSPARSER = True
except ImportError:
    import flowio
    USE_FCSPARSER = False
from loguru import logger
import gc

from .base_parser import BaseParser


class FCSParser(BaseParser):
    """
    Parser for Flow Cytometry Standard (FCS) files.
    
    Features:
    - Memory-efficient chunked processing
    - Automatic sample ID extraction from filename
    - Statistics pre-calculation
    - Quality validation
    - Parquet output with compression
    """
    
    # Support multiple channel naming conventions
    REQUIRED_CHANNELS = [
        ['FSC-A', 'SSC-A'],        # Standard naming
        ['VFSC-A', 'VSSC1-A'],     # Vendor-specific (ZE5, etc.)
        ['FSC-H', 'SSC-H'],        # Alternative naming
    ]
    
    def __init__(
        self, 
        file_path: Path, 
        compensate: bool = False,
        chunk_size: int = 50000
    ):
        """
        Initialize FCS parser.
        
        Args:
            file_path: Path to FCS file
            compensate: Whether to apply compensation matrix (if available)
            chunk_size: Number of events to process at a time
        """
        super().__init__(file_path)
        self.compensate = compensate
        self.chunk_size = chunk_size
        self.channel_names: List[str] = []
        self.sample_id: Optional[str] = None
        self.biological_sample_id: Optional[str] = None
        self.measurement_id: Optional[str] = None
        self.is_baseline: bool = False
        
    def validate(self) -> bool:
        """
        Validate FCS file.
        
        Returns:
            True if file is valid, False otherwise
        """
        try:
            # Check file exists and is readable
            if not self.file_path.exists():
                logger.error(f"File not found: {self.file_path}")
                return False
            
            # Check file size (warn if very large)
            file_size_mb = self.file_path.stat().st_size / (1024 * 1024)
            if file_size_mb > 500:
                logger.warning(f"Large file ({file_size_mb:.1f} MB): {self.file_path.name}")
            
            # Check file extension
            if self.file_path.suffix.lower() != '.fcs':
                logger.warning(f"Unexpected extension: {self.file_path.suffix}")
            
            # Try to read FCS header (first 10 bytes)
            with open(self.file_path, 'rb') as f:
                header = f.read(10).decode('ascii', errors='ignore')
                if not header.startswith('FCS'):
                    logger.error(f"Invalid FCS header: {header[:6]}")
                    return False
            
            logger.info(f"Γ£ô FCS file validated: {self.file_path.name}")
            return True
            
        except Exception as e:
            logger.error(f"Validation failed: {e}")
            return False
    
    def parse(self) -> pd.DataFrame:
        """
        Parse FCS file and return event data as DataFrame.
        Uses memory-efficient chunked processing for large files.
        
        Returns:
            DataFrame with all events and metadata columns
        """
        try:
            logger.info(f"Parsing FCS file: {self.file_path.name}")
            
            if USE_FCSPARSER:
                # Parse FCS file using fcsparser
                meta, data = fcsparser.parse(
                    str(self.file_path),
                    meta_data_only=False,
                    reformat_meta=True
                )
                self.metadata = meta
                self.data = data
            else:
                # Parse FCS file using flowio (numpy 2.x compatible)
                fcs_data = flowio.FlowData(str(self.file_path))
                
                # Get channel names from PnN or PnS parameters
                # FCS metadata keys can be lowercase (p1n, p1s) or uppercase ($P1N, $P1S)
                channel_count = fcs_data.channel_count
                channel_names = []
                for i in range(1, channel_count + 1):
                    # Try multiple key formats - prefer short name (PnS) which has descriptive names like VFSC-A
                    # Check lowercase keys first (flowio returns lowercase), then uppercase
                    name = (
                        fcs_data.text.get(f'p{i}s', '') or  # lowercase short name (preferred - VFSC-A, VSSC1-A)
                        fcs_data.text.get(f'p{i}n', '') or  # lowercase full name (FSC-A, SSC-A)
                        fcs_data.text.get(f'$P{i}S', '') or  # uppercase with $ prefix
                        fcs_data.text.get(f'$P{i}N', '') or  # uppercase with $ prefix
                        fcs_data.text.get(f'P{i}S', '') or   # uppercase without $
                        fcs_data.text.get(f'P{i}N', '') or   # uppercase without $
                        f'Channel_{i}'
                    )
                    # Clean up the name
                    name = name.strip()
                    if not name:
                        name = f'Channel_{i}'
                    channel_names.append(name)
                
                logger.info(f"Channel names from metadata: {channel_names[:10]}...")
                
                # Convert events to DataFrame
                events = np.array(fcs_data.events).reshape(-1, channel_count)
                data = pd.DataFrame(events, columns=channel_names)
                
                self.metadata = dict(fcs_data.text)
                self.data = data
            
            # Extract identifiers from filename
            self._extract_identifiers()
            
            # Get channel names
            self.channel_names = list(data.columns)
            logger.info(f"Found {len(self.channel_names)} channels: {self.channel_names[:5]}...")
            
            # Add metadata columns
            # Type assertion: data is guaranteed to be DataFrame at this point
            data = self.data  # type: pd.DataFrame
            data['sample_id'] = self.sample_id
            data['biological_sample_id'] = self.biological_sample_id
            data['measurement_id'] = self.measurement_id
            data['is_baseline'] = self.is_baseline
            data['file_name'] = self.file_path.name
            data['instrument_type'] = 'flow_cytometry'
            data['parse_timestamp'] = pd.Timestamp.now()
            self.data = data
            
            # Apply compensation if requested
            if self.compensate and self._has_compensation_matrix():
                logger.info("Applying compensation matrix...")
                if self.data is not None:
                    self.data = self._apply_compensation(self.data)
            
            if self.data is not None:
                logger.info(f"Γ£ô Parsed {len(self.data):,} events from {self.file_path.name}")
            
            # Force garbage collection
            gc.collect()
            
            if self.data is None:
                raise ValueError("Parsing failed: data is None")
            
            return self.data
            
        except Exception as e:
            logger.error(f"Failed to parse FCS file: {e}")
            raise
    
    def _extract_identifiers(self) -> None:
        """
        Extract sample identifiers from filename.
        
        Filename patterns:
        - P5_F10_ISO.fcs          -> biological_sample_id: P5_F10, is_baseline: True
        - P5_F10_CD81_0.25ug.fcs  -> biological_sample_id: P5_F10, is_baseline: False
        - Exo+1ug CD81 SEC.fcs    -> biological_sample_id: Exo, is_baseline: False
        
        HOW IT WORKS:
        -------------
        1. Get filename without extension (.stem removes .fcs)
        2. Check for baseline keywords (ISO, Isotype, control)
        3. Try multiple pattern-matching strategies in order of specificity
        4. Extract biological_sample_id (identifies the biological sample)
        5. Set measurement_id (unique ID for this specific measurement)
        """
        # Get filename without .fcs extension
        # Example: "P5_F10_CD81.fcs" → "P5_F10_CD81"
        filename = self.file_path.stem
        
        # Step 1: Detect baseline (isotype control) samples
        # -----------------------------------------------------
        # Baselines use non-specific antibodies to measure background
        # Look for keywords that indicate this is a control sample
        iso_keywords = ['ISO', 'Isotype', 'isotype', 'control']
        self.is_baseline = any(keyword in filename for keyword in iso_keywords)
        # Example: "P5_F10_ISO.fcs" → is_baseline=True
        #          "P5_F10_CD81.fcs" → is_baseline=False
        
        # Step 2: Try to extract biological sample ID using pattern matching
        # -------------------------------------------------------------------
        # Try multiple patterns because different experiments use different naming
        
        # Pattern 1: P{passage}_F{fraction}_... format
        # --------------------------------------------
        # Example: "P5_F10_CD81.fcs" → P5 (passage 5), F10 (fraction 10)
        # This format is used for iPSC-derived exosomes
        if filename.startswith('P') and '_F' in filename:
            # Split by underscore: ["P5", "F10", "CD81"]
            parts = filename.split('_')
            if len(parts) >= 2:
                # Take first two parts: "P5" and "F10"
                self.biological_sample_id = f"{parts[0]}_{parts[1]}"  # "P5_F10"
                # Measurement ID includes antibody: "P5_F10_CD81"
                self.measurement_id = filename
        
        # Pattern 2: L{lot}+F{fraction}+... format
        # -----------------------------------------
        # Example: "L5+F10+CD81.fcs" → L5 (lot 5), F10 (fraction 10)
        # This format uses + separators instead of underscores
        elif 'L' in filename and 'F' in filename and '+' in filename:
            # Split by +: ["L5", "F10", "CD81"]
            parts = filename.split('+')
            if len(parts) >= 2:
                lot = parts[0].strip()      # "L5"
                fraction = parts[1].strip()  # "F10"
                # Combine with underscore for consistency: "L5_F10"
                self.biological_sample_id = f"{lot}_{fraction}"
                self.measurement_id = filename
        
        # Pattern 3: Exo+... format (generic exosome samples)
        # ---------------------------------------------------
        # Example: "Exo+1ug CD81 SEC.fcs"
        # Used for exosome samples with antibody concentration and method
        elif filename.startswith('Exo'):
            # Biological sample is just "Exo" (not specific passage/fraction)
            self.biological_sample_id = 'Exo'
            # Measurement ID includes full details: antibody + concentration + method
            self.measurement_id = filename
        
        # Fallback: Use entire filename if no pattern matches
        # ---------------------------------------------------
        # For files that don't match known patterns, use full filename
        else:
            self.biological_sample_id = filename
            self.measurement_id = filename
        
        # Step 3: Generate unique sample_id for internal tracking
        # --------------------------------------------------------
        # For now, same as measurement_id (can be made more unique if needed)
        self.sample_id = self.measurement_id
        
        # Log the extracted identifiers for debugging
        logger.info(f"Extracted IDs: biological={self.biological_sample_id}, "
                   f"measurement={self.measurement_id}, baseline={self.is_baseline}")
    
    def extract_metadata(self) -> Dict[str, Any]:
        """
        Extract relevant metadata from FCS file.
        
        Returns:
            Dictionary of metadata
        """
        if not self.metadata:
            raise ValueError("No metadata available. Call parse() first.")
        
        # Extract key metadata fields
        extracted = {
            'sample_id': self.sample_id,
            'biological_sample_id': self.biological_sample_id,
            'measurement_id': self.measurement_id,
            'is_baseline': self.is_baseline,
            'file_name': self.file_path.name,
            'instrument_type': 'flow_cytometry',
            'total_events': int(self.metadata.get('$TOT', 0)),
            'parameters': int(self.metadata.get('$PAR', 0)),
            'acquisition_date': self.metadata.get('$DATE', 'Unknown'),
            'acquisition_time': self.metadata.get('$BTIM', 'Unknown'),
            'cytometer': self.metadata.get('$CYT', 'Unknown'),
            'operator': self.metadata.get('$OP', 'Unknown'),
            'specimen': self.metadata.get('$SMNO', 'Unknown'),
        }
        
        # Extract channel information
        channels = {}
        n_params = int(self.metadata.get('$PAR', 0))
        
        for i in range(1, n_params + 1):
            name = self.metadata.get(f'$P{i}N', f'Param{i}')
            stain = self.metadata.get(f'$P{i}S', 'Unstained')
            range_val = self.metadata.get(f'$P{i}R', 'Unknown')
            
            channels[name] = {
                'stain': stain,
                'range': range_val,
                'index': i
            }
        
        extracted['channels'] = channels
        extracted['channel_count'] = len(channels)
        extracted['channel_names'] = list(channels.keys())
        
        # Temperature if available
        if '$TEMP' in self.metadata:
            extracted['temperature'] = float(self.metadata['$TEMP'])
        
        return extracted
    
    def _has_compensation_matrix(self) -> bool:
        """Check if compensation matrix is available in metadata."""
        return '$COMP' in self.metadata or '$SPILLOVER' in self.metadata
    
    def _apply_compensation(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Apply compensation matrix to data.
        
        Note: Full implementation depends on compensation format.
        This is a placeholder for future implementation.
        """
        logger.warning("Compensation not yet fully implemented")
        return data
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Calculate comprehensive statistics for each channel.
        Pre-calculates stats to avoid loading raw events for every analysis.
        
        Returns:
            Dictionary of channel statistics
        """
        if self.data is None:
            raise ValueError("No data available. Call parse() first.")
        
        stats = {}
        numeric_cols = self.data.select_dtypes(include=[np.number]).columns
        
        for col in numeric_cols:
            if col in self.channel_names:
                series = self.data[col]
                mean_val = series.mean()
                std_val = series.std()
                
                # Calculate skewness and kurtosis - handle potential complex numbers
                skew_val = series.skew()
                kurt_val = series.kurtosis()
                
                # Convert to float, handling complex numbers if they occur
                if isinstance(skew_val, complex):
                    skew_float = float(skew_val.real)
                else:
                    skew_float = float(skew_val)
                
                if isinstance(kurt_val, complex):
                    kurt_float = float(kurt_val.real)
                else:
                    kurt_float = float(kurt_val)
                
                stats[col] = {
                    'mean': float(mean_val),
                    'median': float(series.median()),
                    'std': float(std_val),
                    'min': float(series.min()),
                    'max': float(series.max()),
                    'q10': float(series.quantile(0.10)),
                    'q25': float(series.quantile(0.25)),
                    'q50': float(series.quantile(0.50)),
                    'q75': float(series.quantile(0.75)),
                    'q90': float(series.quantile(0.90)),
                    'q95': float(series.quantile(0.95)),
                    'cv': float(std_val / mean_val) if mean_val != 0 else 0,
                    'iqr': float(series.quantile(0.75) - series.quantile(0.25)),
                    'skewness': skew_float,
                    'kurtosis': kurt_float,
                }
        
        # Add overall statistics
        stats['_summary'] = {
            'total_events': len(self.data),
            'sample_id': self.sample_id,
            'biological_sample_id': self.biological_sample_id,
            'measurement_id': self.measurement_id,
            'is_baseline': self.is_baseline,
            'channel_count': len(self.channel_names),
            'channels': self.channel_names,
        }
        
        return stats
    
    def validate_quality(self) -> Dict[str, Any]:
        """
        Perform quality validation checks on parsed data.
        
        Returns:
            Dictionary with QC results
        """
        if self.data is None:
            raise ValueError("No data available. Call parse() first.")
        
        qc_results = {
            'passed': True,
            'warnings': [],
            'errors': [],
        }
        
        # Check 1: Minimum event count
        event_count = len(self.data)
        if event_count < 1000:
            qc_results['passed'] = False
            qc_results['errors'].append(
                f"Insufficient events: {event_count} < 1000"
            )
        
        # Check 2: Required channels present (check all naming conventions)
        channels_found = False
        for channel_set in self.REQUIRED_CHANNELS:
            if all(ch in self.data.columns for ch in channel_set):
                channels_found = True
                qc_results['detected_channels'] = channel_set
                break
        
        if not channels_found:
            qc_results['passed'] = False
            qc_results['errors'].append(
                f"Missing required scatter channels. Expected one of: {self.REQUIRED_CHANNELS}"
            )
        
        # Check 3: Check for negative FSC/SSC values (should be rare)
        fsc_cols = [col for col in self.data.columns if 'FSC' in col and '-A' in col]
        ssc_cols = [col for col in self.data.columns if 'SSC' in col and '-A' in col]
        
        for col in fsc_cols + ssc_cols:
            neg_count = (self.data[col] < 0).sum()
            if neg_count > len(self.data) * 0.01:  # More than 1% negative
                qc_results['warnings'].append(
                    f"High negative {col} values: {neg_count} events ({neg_count/len(self.data)*100:.1f}%)"
                )
        
        # Check 4: Data completeness (no NaN)
        nan_count = self.data.isnull().sum().sum()
        if nan_count > 0:
            qc_results['warnings'].append(
                f"Missing values detected: {nan_count} NaN entries"
            )
        
        # Check 5: Extreme outliers (beyond typical flow cytometry range)
        for col in self.channel_names:
            if col in self.data.columns:
                max_val = self.data[col].max()
                # Typical max for flow cytometry is 2^18 (262144) or 2^20 (1048576)
                if max_val > 1048576:
                    qc_results['warnings'].append(
                        f"Unusually high values in {col}: max={max_val:.0f}"
                    )
        
        # Check 6: Event count consistency
        expected_events = int(self.metadata.get('$TOT', 0))
        actual_events = len(self.data)
        if expected_events > 0 and abs(expected_events - actual_events) > 10:
            qc_results['warnings'].append(
                f"Event count mismatch: expected {expected_events}, got {actual_events}"
            )
        
        return qc_results
