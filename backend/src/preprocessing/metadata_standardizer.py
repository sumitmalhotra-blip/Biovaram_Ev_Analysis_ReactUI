"""
Metadata Standardization Module
================================

Purpose: Standardize sample metadata from user uploads for backend processing

Meeting Decision (Nov 18, 2025):
- Do NOT rely on user filenames for metadata extraction
- Different users/labs will use different naming conventions
- SOLUTION: Capture metadata via UI popup, standardize internally

Author: CRMIT Backend Team
Date: November 18, 2025
"""

from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass
import re
from loguru import logger


@dataclass
class SampleMetadata:
    """Standardized sample metadata structure."""
    
    # Required fields
    biological_sample_id: str  # e.g., "P5_F10" or "IPSC_P2"
    treatment: str  # e.g., "CD81", "CD9", "ISO", "Control"
    
    # Optional fields
    concentration_ug: Optional[float] = None  # Antibody concentration
    preparation_method: Optional[str] = None  # "SEC", "Centrifugation", "Filtration"
    passage_number: Optional[int] = None  # Cell passage number
    fraction_number: Optional[int] = None  # Fraction number
    experiment_date: Optional[str] = None  # ISO format: YYYY-MM-DD
    operator: Optional[str] = None
    notes: Optional[str] = None
    
    # Auto-generated
    upload_timestamp: Optional[str] = None
    original_filename: Optional[str] = None
    internal_filename: Optional[str] = None


class MetadataStandardizer:
    """
    Standardize sample metadata for consistent backend processing.
    
    Meeting Context (Nov 18, 2025):
    Parvesh: "Realistically speaking, they won't do it [follow naming convention]. 
              So, we should do it from our side. What we can do is have a popup 
              when they put the file in asking for like basic details..."
    
    Approach:
    1. User uploads file with ANY name
    2. UI popup captures metadata
    3. Backend generates standardized internal name
    4. User keeps original name for their records
    5. Model uses standardized names internally
    """
    
    def __init__(self):
        self.treatment_codes = {
            'CD81': 'CD81',
            'CD9': 'CD9',
            'CD63': 'CD63',
            'ISO': 'ISO',
            'Isotype': 'ISO',
            'Control': 'CTRL',
            'Blank': 'BLANK',
            'Water': 'WATER'
        }
        
        self.method_codes = {
            'SEC': 'SEC',
            'Size Exclusion Chromatography': 'SEC',
            'Centrifugation': 'CENTRI',
            'Ultracentrifugation': 'CENTRI',
            'Filtration': 'FILTER',
            '0.2um Filter': 'FILTER',
            '0.22um Filter': 'FILTER'
        }
    
    def generate_internal_filename(
        self,
        metadata: SampleMetadata,
        instrument_type: str,
        file_extension: str = '.parquet'
    ) -> str:
        """
        Generate standardized internal filename from metadata.
        
        Format: {bio_sample_id}_{treatment}_{conc}ug_{method}_{date}_{instrument}{ext}
        Example: P5_F10_CD81_0.25ug_SEC_20251118_FC.parquet
        
        Args:
            metadata: SampleMetadata object
            instrument_type: 'FC' (FCS/NanoFACS), 'NTA', 'TEM', 'WB'
            file_extension: File extension (default: .parquet)
            
        Returns:
            Standardized internal filename
        
        WHAT THIS DOES:
        ----------------
        Converts user-provided metadata into a consistent filename format that:
        - Uniquely identifies each sample
        - Is sortable and searchable
        - Contains key experimental parameters
        - Works across different operating systems
        
        HOW IT WORKS:
        --------------
        Step-by-step filename construction:
        
        1. Start with biological sample ID (e.g., "P5_F10" or "IPSC_P2")
           - Identifies the source biological material
        
        2. Add treatment/antibody (e.g., "CD81", "ISO", "CTRL")
           - Standardized codes from self.treatment_codes
           - Example: "Isotype" → "ISO"
        
        3. Add concentration if specified (e.g., "0.25ug", "1ug", "2ug")
           - Only included if concentration_ug is not None
        
        4. Add preparation method if specified (e.g., "SEC", "CENTRI", "FILTER")
           - Standardized codes from self.method_codes
           - Example: "Size Exclusion Chromatography" → "SEC"
        
        5. Add date (e.g., "20251118")
           - Uses experiment_date if provided, otherwise today's date
           - Format: YYYYMMDD (sortable)
        
        6. Add instrument type (e.g., "FC", "NTA", "TEM")
           - Indicates which instrument generated the data
        
        7. Join with underscores and add file extension
        
        WHY THIS DESIGN:
        ----------------
        - User filenames are inconsistent: "my_random_file_123.fcs"
        - Different labs use different naming conventions
        - Need standardization for:
          - Database queries (find all CD81 samples)
          - Sorting (by date, sample, treatment)
          - Matching across instruments (FCS + NTA + TEM for same sample)
        - Underscores allow easy parsing back into components
        
        EXAMPLE TRANSFORMATIONS:
        ------------------------
        User: "my_file_today.fcs"
        Metadata: {bio_sample_id: "P5_F10", treatment: "CD81", conc: 0.25, method: "SEC", date: "2025-11-18"}
        Output: "P5_F10_CD81_0.25ug_SEC_20251118_FC.parquet"
        
        User: "test123.csv" (NTA)
        Metadata: {bio_sample_id: "IPSC_P2", treatment: "Control"}
        Output: "IPSC_P2_CTRL_20251118_NTA.parquet"
        """
        parts = []
        
        # Biological sample ID (required)
        parts.append(self._sanitize_id(metadata.biological_sample_id))
        
        # Treatment (required)
        treatment_code = self.treatment_codes.get(metadata.treatment, metadata.treatment)
        parts.append(self._sanitize_id(treatment_code))
        
        # Concentration (if provided)
        if metadata.concentration_ug is not None:
            parts.append(f"{metadata.concentration_ug}ug")
        
        # Preparation method (if provided)
        if metadata.preparation_method:
            method_code = self.method_codes.get(
                metadata.preparation_method,
                self._sanitize_id(metadata.preparation_method)
            )
            parts.append(method_code)
        
        # Date (use experiment date or today)
        if metadata.experiment_date:
            date_str = metadata.experiment_date.replace('-', '')
        else:
            date_str = datetime.now().strftime('%Y%m%d')
        parts.append(date_str)
        
        # Instrument type
        parts.append(instrument_type)
        
        # Join and add extension
        filename = '_'.join(parts) + file_extension
        
        logger.info(f"📝 Generated internal filename: {filename}")
        return filename
    
    def _sanitize_id(self, id_str: str) -> str:
        """Remove special characters and spaces from ID."""
        # Remove special characters, keep alphanumeric and underscore
        sanitized = re.sub(r'[^\w\-]', '', id_str)
        # Replace multiple underscores with single
        sanitized = re.sub(r'_+', '_', sanitized)
        return sanitized.strip('_')
    
    def parse_from_popup(self, popup_data: Dict[str, Any]) -> SampleMetadata:
        """
        Parse metadata from UI popup form data.
        
        Args:
            popup_data: Dictionary from UI form with keys:
                - bio_sample_id (required)
                - treatment (required)
                - concentration_ug (optional)
                - preparation_method (optional)
                - passage_number (optional)
                - fraction_number (optional)
                - experiment_date (optional)
                - operator (optional)
                - notes (optional)
                - original_filename (auto)
                
        Returns:
            SampleMetadata object
        """
        metadata = SampleMetadata(
            biological_sample_id=popup_data['bio_sample_id'],
            treatment=popup_data['treatment'],
            concentration_ug=popup_data.get('concentration_ug'),
            preparation_method=popup_data.get('preparation_method'),
            passage_number=popup_data.get('passage_number'),
            fraction_number=popup_data.get('fraction_number'),
            experiment_date=popup_data.get('experiment_date'),
            operator=popup_data.get('operator'),
            notes=popup_data.get('notes'),
            upload_timestamp=datetime.now().isoformat(),
            original_filename=popup_data.get('original_filename')
        )
        
        logger.info(f"✅ Parsed metadata for sample: {metadata.biological_sample_id}")
        return metadata
    
    def validate_metadata(self, metadata: SampleMetadata) -> tuple[bool, list[str]]:
        """
        Validate required fields in metadata.
        
        Args:
            metadata: SampleMetadata to validate
            
        Returns:
            Tuple of (is_valid, error_messages)
        
        WHAT THIS DOES:
        ----------------
        Checks that user-provided metadata meets minimum requirements before
        the file is processed. Prevents bad data from entering the system.
        
        HOW IT WORKS:
        --------------
        Validation checks:
        
        1. Required field checks:
           - biological_sample_id: MUST be provided (identifies the sample)
           - treatment: MUST be provided (what antibody/condition was tested)
        
        2. Value range checks:
           - concentration_ug: If provided, must be ≥ 0 (negative concentration is nonsensical)
           - passage_number: If provided, must be ≥ 0 (cell passage can't be negative)
        
        3. Error accumulation:
           - Collects ALL errors, not just first one
           - Returns complete list so user can fix everything at once
        
        WHY THIS DESIGN:
        ----------------
        - Better UX: Show all problems at once, not one at a time
        - Data integrity: Catch issues before processing (expensive to fix later)
        - Debugging: Clear error messages help users understand what's wrong
        
        EXAMPLE SCENARIOS:
        ------------------
        ✅ VALID:
        {
            bio_sample_id: "P5_F10",
            treatment: "CD81",
            concentration_ug: 0.25
        }
        → (True, [])
        
        ❌ INVALID:
        {
            bio_sample_id: "",  # Missing!
            treatment: "CD81",
            concentration_ug: -5  # Negative!
        }
        → (False, ["Biological Sample ID is required", "Concentration must be positive"])
        """
        errors = []
        
        # Required fields
        if not metadata.biological_sample_id:
            errors.append("Biological Sample ID is required")
        
        if not metadata.treatment:
            errors.append("Treatment/Antibody is required")
        
        # Validation rules
        if metadata.concentration_ug is not None and metadata.concentration_ug < 0:
            errors.append("Concentration must be positive")
        
        if metadata.passage_number is not None and metadata.passage_number < 0:
            errors.append("Passage number must be positive")
        
        is_valid = len(errors) == 0
        
        if is_valid:
            logger.info(f"✅ Metadata validation passed for {metadata.biological_sample_id}")
        else:
            logger.error(f"❌ Metadata validation failed: {', '.join(errors)}")
        
        return is_valid, errors
    
    def create_sample_registry_entry(
        self,
        metadata: SampleMetadata,
        internal_filename: str,
        instrument_type: str,
        file_path: Path
    ) -> Dict[str, Any]:
        """
        Create entry for sample metadata registry (master database).
        
        This will be stored in: unified_data/samples/sample_metadata.parquet
        
        Args:
            metadata: SampleMetadata object
            internal_filename: Generated internal filename
            instrument_type: 'flow_cytometry', 'nta', 'tem', 'western_blot'
            file_path: Path to processed file
            
        Returns:
            Dictionary for sample registry
        """
        entry = {
            # Primary key
            'sample_id': internal_filename.replace('.parquet', ''),
            
            # Biological information
            'biological_sample_id': metadata.biological_sample_id,
            'treatment': metadata.treatment,
            'concentration_ug': metadata.concentration_ug,
            'preparation_method': metadata.preparation_method,
            'passage_number': metadata.passage_number,
            'fraction_number': metadata.fraction_number,
            
            # Experimental context
            'experiment_date': metadata.experiment_date,
            'operator': metadata.operator,
            'notes': metadata.notes,
            
            # File tracking
            'original_filename': metadata.original_filename,
            'internal_filename': internal_filename,
            'file_path': str(file_path),
            'instrument_type': instrument_type,
            
            # Metadata
            'upload_timestamp': metadata.upload_timestamp,
            'processing_status': 'pending',
            'qc_status': 'not_checked'
        }
        
        logger.info(f"📋 Created registry entry for {entry['sample_id']}")
        return entry


# Example usage and testing
if __name__ == "__main__":
    # Example: User uploads file via UI
    standardizer = MetadataStandardizer()
    
    # Simulate popup form data
    popup_data = {
        'bio_sample_id': 'P5_F10',
        'treatment': 'CD81',
        'concentration_ug': 0.25,
        'preparation_method': 'SEC',
        'experiment_date': '2025-11-18',
        'operator': 'Researcher1',
        'original_filename': 'my_random_file_name_123.fcs'
    }
    
    # Parse metadata
    metadata = standardizer.parse_from_popup(popup_data)
    
    # Validate
    is_valid, errors = standardizer.validate_metadata(metadata)
    print(f"Valid: {is_valid}")
    if errors:
        print(f"Errors: {errors}")
    
    # Generate internal filename
    internal_name = standardizer.generate_internal_filename(
        metadata,
        instrument_type='FC',
        file_extension='.parquet'
    )
    print(f"Internal filename: {internal_name}")
    
    # Create registry entry
    registry_entry = standardizer.create_sample_registry_entry(
        metadata,
        internal_name,
        'flow_cytometry',
        Path(f"data/parquet/nanofacs/events/{internal_name}")
    )
    print("\nRegistry entry:")
    for key, value in registry_entry.items():
        print(f"  {key}: {value}")
