"""
NTA Parser for ZetaView Nanoparticle Tracking Analysis Files
Supports size distribution, zeta potential, and 11-position uniformity measurements
"""

from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
import pandas as pd
import numpy as np
import re
from datetime import datetime
from loguru import logger

from .base_parser import BaseParser


class NTAParser(BaseParser):
    """Parser for Nanoparticle Tracking Analysis (NTA) text files from ZetaView."""
    
    # File type detection patterns
    FILE_TYPE_PATTERNS = {
        'size': r'_size_\d+',  # Size distribution files
        'prof': r'_prof_\d+',  # Zeta potential profile files
        '11pos': r'_11pos',    # 11-position uniformity measurements
    }
    
    def __init__(self, file_path: Path | str):
        """
        Initialize NTA parser.
        
        Args:
            file_path: Path to NTA text file (Path object or string)
        """
        super().__init__(Path(file_path) if isinstance(file_path, str) else file_path)
        self.sample_id: Optional[str] = None
        self.measurement_type: Optional[str] = None
        self.measurement_params: Dict[str, Any] = {}
        self.raw_metadata: Dict[str, str] = {}
        
    def validate(self) -> bool:
        """
        Validate NTA text file format.
        
        Returns:
            True if file is valid ZetaView NTA format
        """
        try:
            if not self.file_path.exists():
                logger.error(f"File not found: {self.file_path}")
                return False
            
            # Check file extension
            if self.file_path.suffix.lower() not in ['.txt', '.tsv']:
                logger.warning(f"Unexpected extension: {self.file_path.suffix}")
            
            # Try to read first few lines
            with open(self.file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read(5000)  # Read first 5KB
                
            # Check for ZetaView signature or expected content
            indicators = ['ZetaView', 'Size Distribution', 'Profile Data', 
                         'Concentration', 'Sample:', 'Operator:']
            
            if not any(indicator in content for indicator in indicators):
                logger.warning(f"File may not be ZetaView NTA format: {self.file_path.name}")
            
            logger.info(f"Γ£ô NTA file validated: {self.file_path.name}")
            return True
            
        except Exception as e:
            logger.error(f"Validation failed for {self.file_path.name}: {e}")
            return False
    
    def parse(self) -> pd.DataFrame:
        """
        Parse NTA text file and return data.
        
        Returns:
            DataFrame with parsed NTA data
        """
        try:
            # Detect file type from filename
            self.measurement_type = self._detect_file_type()
            logger.info(f"Parsing {self.measurement_type} file: {self.file_path.name}")
            
            # Read file content
            with open(self.file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            lines = content.split('\n')
            
            # Extract metadata
            self.raw_metadata = self._parse_metadata(lines)
            self.sample_id = self._extract_sample_id()
            self._extract_measurement_params()
            
            # Parse data based on file type
            if '11pos' in self.measurement_type:
                self.data = self._parse_11pos_data(lines)
            elif 'prof' in self.measurement_type:
                self.data = self._parse_profile_data(lines)
            elif 'size' in self.measurement_type:
                self.data = self._parse_size_distribution(lines)
            else:
                # Fallback: try size distribution
                self.data = self._parse_size_distribution(lines)
            
            # Add metadata columns
            self._add_metadata_columns()
            
            logger.info(f"Γ£ô Parsed {len(self.data)} data points from {self.file_path.name}")
            
            return self.data
            
        except Exception as e:
            logger.error(f"Failed to parse NTA file {self.file_path.name}: {e}")
            raise
    
    def _detect_file_type(self) -> str:
        """
        Detect NTA file type from filename.
        
        Returns:
            File type string ('size', 'prof', 'size_11pos', 'prof_11pos')
        """
        filename = self.file_path.name.lower()
        
        file_types = []
        if '_11pos' in filename:
            file_types.append('11pos')
        if '_prof_' in filename:
            file_types.append('prof')
        elif '_size_' in filename:
            file_types.append('size')
        
        if not file_types:
            logger.warning(f"Could not detect file type for {filename}, assuming size distribution")
            return 'size'
        
        return '_'.join(file_types)
    
    def _parse_metadata(self, lines: List[str]) -> Dict[str, str]:
        """
        Extract metadata from header lines.
        
        Args:
            lines: File content split by newlines
            
        Returns:
            Dictionary of metadata key-value pairs
        """
        metadata = {}
        
        # Metadata patterns
        patterns = [
            (r'Original File:\s*(.+)', 'original_file'),
            (r'Operator:\s*(.+)', 'operator'),
            (r'Experiment:\s*(\S+)', 'experiment'),
            (r'ZetaView S/N:\s*(.+)', 'instrument_serial'),
            (r'Cell S/N:\s*(.+)', 'cell_serial'),
            (r'Software:\s*ZetaView \(version\s+([^\)]+)\)', 'software_version'),
            (r'SOP:\s*(.+)', 'sop'),
            (r'Sample:\s*(.+)', 'sample_name'),
            (r'Electrolyte:\s*(.+)', 'electrolyte'),
            (r'pH:\s*([0-9.]+)', 'ph'),
            (r'Conductivity:\s*([0-9.]+)', 'conductivity'),
            (r'Temperature:\s*([0-9.]+)', 'temperature'),
            (r'Viscosity:\s*([0-9.]+)', 'viscosity'),
            (r'Date:\s*([0-9\-]+)', 'date'),
            (r'Time:\s*([0-9:]+)', 'time'),
            (r'Scattering Intensity:\s*([0-9.]+)', 'scattering_intensity'),
            (r'Detected Particles:\s*([0-9]+)', 'detected_particles'),
            (r'Cell Check Result:\s*(.+)', 'cell_check_result'),
            (r'Type of Measurement:\s*(.+)', 'measurement_type'),
            (r'Positions:\s*([0-9]+)', 'num_positions'),
            (r'Number of Traces:\s*([0-9]+)', 'num_traces'),
            (r'Average Number of Particles:\s*([0-9.]+)', 'avg_particles'),
            (r'Dilution::\s*([0-9.]+)', 'dilution'),
            (r'Concentration Correction Factor:\s*([0-9.]+)', 'conc_correction'),
            (r'Minimum Brightness:\s*([0-9]+)', 'min_brightness'),
            (r'Minimum Area:\s*([0-9]+)', 'min_area'),
            (r'Maximum Area:\s*([0-9]+)', 'max_area'),
            (r'Sensitivity:\s*([0-9.]+)', 'sensitivity'),
            (r'Shutter:\s*([0-9.]+)', 'shutter'),
            (r'Laser Wavelength nm:\s*([0-9.]+)', 'laser_wavelength'),
        ]
        
        # Extract metadata from first 200 lines
        for line in lines[:200]:
            for pattern, key in patterns:
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    metadata[key] = match.group(1).strip()
        
        return metadata
    
    def _extract_sample_id(self) -> str:
        """
        Extract sample ID from metadata or filename.
        
        Returns:
            Sample ID string
        """
        # Try to get from metadata
        if 'sample_name' in self.raw_metadata:
            return self.raw_metadata['sample_name']
        
        # Parse from filename
        # Example: 20250227_0002_EV_IP_P2_F2-1000_size_488.txt
        filename = self.file_path.stem
        
        # Remove date prefix (YYYYMMDD_####_)
        pattern = r'^\d{8}_\d{4}_(.+?)(?:_size|_prof|_11pos)'
        match = re.search(pattern, filename)
        if match:
            return match.group(1)
        
        # Fallback: use filename without extension
        return filename
    
    def _extract_measurement_params(self) -> None:
        """Extract numeric measurement parameters from metadata."""
        numeric_keys = [
            'ph', 'conductivity', 'temperature', 'viscosity',
            'scattering_intensity', 'detected_particles', 'num_positions',
            'num_traces', 'avg_particles', 'dilution', 'conc_correction',
            'min_brightness', 'min_area', 'max_area', 'sensitivity',
            'shutter', 'laser_wavelength'
        ]
        
        for key in numeric_keys:
            if key in self.raw_metadata:
                try:
                    value = float(self.raw_metadata[key])
                    self.measurement_params[key] = value
                except (ValueError, TypeError):
                    pass
    
    def _parse_size_distribution(self, lines: List[str]) -> pd.DataFrame:
        """
        Parse size distribution data section.
        
        Args:
            lines: File content split by newlines
            
        Returns:
            DataFrame with size distribution data
        """
        # Find "Size Distribution" header
        data_start_idx = None
        for i, line in enumerate(lines):
            if 'Size Distribution' in line and i < len(lines) - 2:
                # Next line should be column headers
                if 'Size' in lines[i+1] or 'Size / nm' in lines[i+1]:
                    data_start_idx = i + 1
                    break
        
        if data_start_idx is None:
            logger.warning("Could not find 'Size Distribution' section")
            return pd.DataFrame()
        
        # Get header line
        header_line = lines[data_start_idx]
        
        # Detect delimiter
        if '\t' in header_line:
            delimiter = '\t'
        else:
            delimiter = r'\s{2,}'  # Multiple spaces
        
        # Parse headers
        headers = [h.strip() for h in re.split(delimiter, header_line) if h.strip()]
        
        # Parse data rows
        data_rows = []
        for line in lines[data_start_idx + 1:]:
            line = line.strip()
            
            # Stop at end markers or negative size
            if not line or line.startswith('---') or line.startswith('-1.'):
                break
            
            # Skip comment lines
            if line.startswith('#'):
                continue
            
            # Split by delimiter
            values = [v.strip() for v in re.split(delimiter, line) if v.strip()]
            
            # Check if we have the right number of values
            if len(values) == len(headers):
                data_rows.append(values)
        
        if not data_rows:
            logger.warning("No size distribution data found")
            return pd.DataFrame()
        
        # Create DataFrame
        df = pd.DataFrame(data_rows, columns=headers)  # type: ignore[call-overload]
        
        # Convert to numeric
        for col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Standardize column names
        df = self._standardize_column_names(df, data_type='size')
        
        return df
    
    def _parse_profile_data(self, lines: List[str]) -> pd.DataFrame:
        """
        Parse zeta potential profile data section.
        
        Args:
            lines: File content split by newlines
            
        Returns:
            DataFrame with profile data
        """
        # Find "ZP Profile:" header
        data_start_idx = None
        for i, line in enumerate(lines):
            if 'ZP Profile:' in line and i < len(lines) - 2:
                # Next line should be column headers
                data_start_idx = i + 1
                break
        
        if data_start_idx is None:
            logger.warning("Could not find 'ZP Profile' section")
            return pd.DataFrame()
        
        # Get header line
        header_line = lines[data_start_idx]
        
        # Use tab delimiter for profile data
        headers = [h.strip() for h in header_line.split('\t') if h.strip()]
        
        # Parse data rows
        data_rows = []
        for line in lines[data_start_idx + 1:]:
            # Skip empty lines
            if not line or not line.strip():
                continue
            
            # Stop at next section or end
            if line.strip().startswith('---') or len(line.strip()) < 5:
                break
            
            # Split by tabs or multiple spaces
            if '\t' in line:
                values = [v.strip() for v in line.split('\t') if v.strip()]
            else:
                values = [v.strip() for v in re.split(r'\s+', line.strip()) if v.strip()]
            
            # Only accept rows with correct number of columns
            if len(values) >= len(headers) - 1:  # Allow missing last column
                # Pad with None if needed
                while len(values) < len(headers):
                    values.append(None)  # type: ignore[arg-type]
                data_rows.append(values[:len(headers)])
        
        if not data_rows:
            logger.warning("No profile data found")
            return pd.DataFrame()
        
        # Create DataFrame
        df = pd.DataFrame(data_rows, columns=headers)  # type: ignore[call-overload]
        
        # Convert to numeric
        for col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Standardize column names
        df = self._standardize_column_names(df, data_type='profile')
        
        return df
    
    def _parse_11pos_data(self, lines: List[str]) -> pd.DataFrame:
        """
        Parse 11-position uniformity measurement data.
        
        Args:
            lines: File content split by newlines
            
        Returns:
            DataFrame with 11-position data
        """
        # Find "Use\tPosition" or "Use     Position" header (TSV format)
        data_start_idx = None
        for i, line in enumerate(lines):
            # Check for header line with "Use" and "Position"
            if ('Use' in line and 'Position' in line and 
                ('Mean Int' in line or 'Av. No' in line)):
                data_start_idx = i
                break
        
        if data_start_idx is None:
            logger.warning("Could not find 11-position data header")
            return pd.DataFrame()
        
        # Get header line
        header_line = lines[data_start_idx]
        
        # Split headers by tabs - 11pos files use tab delimiter
        headers = [h.strip() for h in header_line.split('\t') if h.strip()]
        
        # Parse data rows
        data_rows = []
        for line in lines[data_start_idx + 1:]:
            # Skip empty lines
            if not line or not line.strip():
                continue
            
            # Stop at summary rows (Mean, St.Dev, Rel.St.Dev)
            if any(line.strip().startswith(s) for s in ['Mean', 'St.Dev', 'Rel.St.Dev']):
                break
            
            # Split by tabs
            values = [v.strip() for v in line.split('\t') if v.strip()]
            
            # Accept rows with correct number of columns (or close to it)
            if len(values) >= len(headers) - 1:
                # Pad with None if needed
                while len(values) < len(headers):
                    values.append(None)  # type: ignore[arg-type]
                data_rows.append(values[:len(headers)])
        
        if not data_rows:
            logger.warning("No 11-position data found")
            return pd.DataFrame()
        
        # Create DataFrame
        df = pd.DataFrame(data_rows, columns=headers)  # type: ignore[call-overload]
        
        # Convert numeric columns
        for col in df.columns:
            if col not in ['Use', 'Removal']:  # Keep these as strings
                # Try to convert to numeric
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Standardize column names
        df = self._standardize_column_names(df, data_type='11pos')
        
        return df
    
    def _standardize_column_names(self, df: pd.DataFrame, data_type: str) -> pd.DataFrame:
        """
        Standardize column names to consistent format.
        
        Args:
            df: DataFrame with original column names
            data_type: Type of data ('size', 'profile', '11pos')
            
        Returns:
            DataFrame with standardized column names
        """
        rename_map = {}
        
        for col in df.columns:
            col_lower = col.lower().replace('/', '_').replace(' ', '_')
            
            # Common mappings
            if 'size' in col_lower and 'nm' in col_lower:
                rename_map[col] = 'size_nm'
            elif 'orig' in col_lower and 'conc' in col_lower:
                rename_map[col] = 'concentration_particles_cm3'
            elif 'concentration' in col_lower or ('conc.' in col_lower and 'p.' in col_lower):
                rename_map[col] = 'concentration_particles_ml'
            elif 'volume' in col_lower and 'nm' in col_lower:
                rename_map[col] = 'volume_nm3'
            elif 'area' in col_lower and 'nm' in col_lower:
                rename_map[col] = 'area_nm2'
            elif col_lower == 'number':
                rename_map[col] = 'particle_count'
            elif 'position' in col_lower and data_type == 'profile':
                rename_map[col] = 'cell_position'
            elif 'zp' in col_lower.replace('_', ''):
                rename_map[col] = 'zeta_potential_mv'
            elif 'positive' in col_lower and 'v' in col_lower:
                rename_map[col] = 'zp_positive_v'
            elif 'negative' in col_lower and 'v' in col_lower:
                rename_map[col] = 'zp_negative_v'
            elif 'parabola' in col_lower:
                rename_map[col] = 'zp_parabola_fit'
            elif 'mean' in col_lower and 'int' in col_lower:
                rename_map[col] = 'mean_intensity'
            elif 'av.' in col_lower and 'particles' in col_lower:
                rename_map[col] = 'avg_particles'
            elif 'no.' in col_lower and 'traces' in col_lower:
                rename_map[col] = 'num_traces'
            elif 'x50' in col_lower:
                rename_map[col] = 'median_size_nm'
            elif 'peak' in col_lower:
                rename_map[col] = 'peak_size_nm'
            elif 'span' in col_lower:
                rename_map[col] = 'distribution_span'
            elif 'drift' in col_lower:
                rename_map[col] = 'particle_drift_um_s'
            elif 'removal' in col_lower:
                rename_map[col] = 'qc_flag'
        
        if rename_map:
            df = df.rename(columns=rename_map)
        
        return df
    
    def _add_metadata_columns(self) -> None:
        """Add metadata columns to the parsed data."""
        if self.data is None or self.data.empty:
            return
        
        # Add essential metadata
        self.data['sample_id'] = self.sample_id
        self.data['file_name'] = self.file_path.name
        self.data['instrument_type'] = 'nta'
        self.data['measurement_type'] = self.measurement_type
        self.data['parse_timestamp'] = pd.Timestamp.now()
        
        # Add measurement parameters as columns
        for key, value in self.measurement_params.items():
            self.data[f'param_{key}'] = value
        
        # Add date/time if available
        if 'date' in self.raw_metadata and 'time' in self.raw_metadata:
            try:
                dt_str = f"{self.raw_metadata['date']} {self.raw_metadata['time']}"
                self.data['measurement_datetime'] = pd.to_datetime(dt_str)
            except:
                pass
    
    def extract_metadata(self) -> Dict[str, Any]:
        """
        Extract complete metadata dictionary.
        
        Returns:
            Dictionary containing all metadata
        """
        metadata = {
            'file_name': self.file_path.name,
            'file_path': str(self.file_path),
            'sample_id': self.sample_id,
            'measurement_type': self.measurement_type,
            'instrument_type': 'nta',
            'parse_timestamp': datetime.now().isoformat(),
        }
        
        # Add raw metadata
        metadata.update(self.raw_metadata)
        
        # Add measurement parameters
        metadata['measurement_params'] = self.measurement_params
        
        # Add data statistics if data was parsed
        if self.data is not None and not self.data.empty:
            metadata['num_data_points'] = len(self.data)
            metadata['columns'] = list(self.data.columns)
        
        return metadata
    
    def get_summary_statistics(self) -> Dict[str, Any]:
        """
        Calculate summary statistics from parsed NTA data.
        
        Returns:
            Dictionary of summary statistics
        """
        if self.data is None or self.data.empty:
            return {}
        
        stats = {}
        
        # Size distribution statistics
        if 'size_nm' in self.data.columns:
            if 'concentration_particles_ml' in self.data.columns:
                # Weighted statistics
                weights = self.data['concentration_particles_ml'].fillna(0)
                if weights.sum() > 0:
                    stats['mean_size_nm'] = np.average(
                        self.data['size_nm'], 
                        weights=weights
                    )
                    stats['total_concentration'] = weights.sum()
            
            # Percentiles
            if 'particle_count' in self.data.columns:
                counts = self.data['particle_count'].fillna(0)
                if counts.sum() > 0:
                    stats['median_size_nm'] = np.average(
                        self.data['size_nm'],
                        weights=counts
                    )
        
        # 11-position statistics
        if 'position' in self.data.columns and 'concentration_particles_ml' in self.data.columns:
            conc_data = self.data['concentration_particles_ml'].dropna()
            if len(conc_data) > 0:
                stats['mean_concentration'] = conc_data.mean()
                stats['std_concentration'] = conc_data.std()
                stats['cv_concentration_percent'] = (conc_data.std() / conc_data.mean() * 100) if conc_data.mean() > 0 else None
        
        # Zeta potential statistics
        if 'zeta_potential_mv' in self.data.columns:
            zp_data = self.data['zeta_potential_mv'].dropna()
            if len(zp_data) > 0:
                stats['mean_zeta_potential'] = zp_data.mean()
                stats['std_zeta_potential'] = zp_data.std()
        
        return stats
