"""
NTA PDF Report Parser
=====================

TASK-007: Parse PDF reports from ZetaView NTA machines to extract:
- Original concentration (particles/mL)
- Dilution factor
- Mean size
- Mode size
- Other metadata

Client Quote (Surya, Dec 3, 2025):
"That number is not ever mentioned in a text format... it is always mentioned 
only in the PDF file... I was struggling through"

The NTA machine (ZetaView) outputs two types of files:
1. Text file - Contains per-size particle counts and concentrations
2. PDF report - Contains CRITICAL data not in text file

Without the PDF data, we cannot calculate actual particle populations.

Author: CRMIT Backend Team
Date: December 17, 2025
"""

from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List
import re
from dataclasses import dataclass, field
from loguru import logger

try:
    import pdfplumber  # type: ignore[import-untyped]
    PDF_SUPPORT = True
except ImportError:
    pdfplumber = None  # type: ignore[assignment]
    PDF_SUPPORT = False
    logger.warning("pdfplumber not installed. PDF parsing disabled. Run: pip install pdfplumber")


@dataclass
class NTAPDFData:
    """Data extracted from NTA PDF report."""
    
    # Core concentration data
    original_concentration: Optional[float] = None  # particles/mL
    dilution_factor: Optional[int] = None
    true_particle_population: Optional[float] = None  # concentration × dilution
    
    # Size statistics
    mean_size_nm: Optional[float] = None
    mode_size_nm: Optional[float] = None
    median_size_nm: Optional[float] = None
    d10_nm: Optional[float] = None
    d50_nm: Optional[float] = None
    d90_nm: Optional[float] = None
    
    # Sample info
    sample_name: Optional[str] = None
    measurement_date: Optional[str] = None
    operator: Optional[str] = None
    instrument: Optional[str] = None
    
    # Quality metrics
    video_quality: Optional[str] = None
    capture_duration_s: Optional[float] = None
    frames_analyzed: Optional[int] = None
    
    # Metadata
    pdf_file_name: Optional[str] = None
    extraction_successful: bool = False
    extraction_errors: List[str] = field(default_factory=list)
    
    def __post_init__(self) -> None:
        # Calculate true particle population if both values exist
        if self.original_concentration and self.dilution_factor:
            self.true_particle_population = self.original_concentration * self.dilution_factor


class NTAPDFParser:
    """
    Parser for NTA PDF reports (ZetaView format).
    
    Usage:
        parser = NTAPDFParser(pdf_path)
        data = parser.parse()
        print(f"Original concentration: {data.original_concentration}")
        print(f"Dilution factor: {data.dilution_factor}")
        print(f"True population: {data.true_particle_population}")
    """
    
    # Regex patterns for extracting data from PDF text
    # These patterns are designed for ZetaView PDF reports
    PATTERNS = {
        # Concentration patterns - various formats
        'concentration_scientific': r'(?:Original\s*)?[Cc]oncentration[:\s]*(\d+\.?\d*)\s*[×xX*]\s*10\^?(\d+)',
        'concentration_e_notation': r'(?:Original\s*)?[Cc]oncentration[:\s]*(\d+\.?\d*)[Ee](\d+)',
        'concentration_plain': r'(?:Original\s*)?[Cc]oncentration[:\s]*(\d+\.?\d*)\s*(?:particles?/mL|p/mL)',
        
        # Dilution factor patterns
        'dilution': r'[Dd]ilution\s*(?:[Ff]actor)?[:\s]*[x×]?\s*(\d+)',
        'dilution_alt': r'[Dd]iluted?\s*(\d+)[:\s]*1',
        
        # Size patterns
        'mean_size': r'[Mm]ean\s*(?:[Ss]ize)?[:\s]*(\d+\.?\d*)\s*nm',
        'mode_size': r'[Mm]ode\s*(?:[Ss]ize)?[:\s]*(\d+\.?\d*)\s*nm',
        'median_size': r'[Mm]edian\s*(?:[Ss]ize)?[:\s]*(\d+\.?\d*)\s*nm',
        'd10': r'[Dd]10[:\s]*(\d+\.?\d*)\s*nm',
        'd50': r'[Dd]50[:\s]*(\d+\.?\d*)\s*nm',
        'd90': r'[Dd]90[:\s]*(\d+\.?\d*)\s*nm',
        
        # Sample info
        'sample_name': r'[Ss]ample\s*(?:[Nn]ame)?[:\s]*([^\n\r]+)',
        'date': r'[Dd]ate[:\s]*(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})',
        'operator': r'[Oo]perator[:\s]*([^\n\r]+)',
        
        # Quality metrics
        'frames': r'[Ff]rames?\s*(?:[Aa]nalyzed)?[:\s]*(\d+)',
        'duration': r'[Dd]uration[:\s]*(\d+\.?\d*)\s*s',
    }
    
    def __init__(self, pdf_path: Path):
        """
        Initialize parser with PDF file path.
        
        Args:
            pdf_path: Path to the NTA PDF report
        """
        self.pdf_path = Path(pdf_path)
        self.raw_text = ""
        self.pages_text: list = []
        
    def validate(self) -> bool:
        """
        Validate that the file exists and is a PDF.
        
        Returns:
            True if file is valid, False otherwise
        """
        if not PDF_SUPPORT:
            logger.error("PDF parsing not available. Install pdfplumber.")
            return False
            
        if not self.pdf_path.exists():
            logger.error(f"PDF file not found: {self.pdf_path}")
            return False
            
        if self.pdf_path.suffix.lower() != '.pdf':
            logger.error(f"Not a PDF file: {self.pdf_path}")
            return False
            
        # Check file size (warn if very large)
        file_size_mb = self.pdf_path.stat().st_size / (1024 * 1024)
        if file_size_mb > 50:
            logger.warning(f"Large PDF file ({file_size_mb:.1f} MB): {self.pdf_path.name}")
            
        return True
    
    def _extract_text(self) -> bool:
        """
        Extract text from all pages of the PDF.
        
        Returns:
            True if extraction successful, False otherwise
        """
        if not PDF_SUPPORT or pdfplumber is None:
            return False
            
        try:
            with pdfplumber.open(str(self.pdf_path)) as pdf:
                self.pages_text = []
                for page in pdf.pages:
                    page_text = page.extract_text() or ""
                    self.pages_text.append(page_text)
                    
                self.raw_text = "\n".join(self.pages_text)
                
            logger.info(f"Extracted {len(self.pages_text)} pages from PDF")
            logger.debug(f"Total text length: {len(self.raw_text)} characters")
            return True
            
        except Exception as e:
            logger.error(f"Failed to extract text from PDF: {e}")
            return False
    
    def _extract_value(self, pattern: str, text: str) -> Optional[str]:
        """
        Extract first matching value using regex pattern.
        
        Args:
            pattern: Regex pattern with capture group
            text: Text to search
            
        Returns:
            Matched value or None
        """
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if match:
            return match.group(1)
        return None
    
    def _extract_concentration(self, text: str) -> Tuple[Optional[float], str]:
        """
        Extract concentration from text using multiple pattern strategies.
        
        Args:
            text: Full PDF text
            
        Returns:
            Tuple of (concentration in particles/mL, extraction method used)
        """
        # Try scientific notation first (most common in ZetaView)
        # Pattern: "3.5 × 10^10" or "3.5 x 10^10"
        match = re.search(self.PATTERNS['concentration_scientific'], text, re.IGNORECASE)
        if match:
            mantissa = float(match.group(1))
            exponent = int(match.group(2))
            concentration = mantissa * (10 ** exponent)
            logger.info(f"Extracted concentration (scientific): {mantissa} × 10^{exponent} = {concentration:.2e}")
            return concentration, "scientific"
        
        # Try E notation: "3.5E10"
        match = re.search(self.PATTERNS['concentration_e_notation'], text, re.IGNORECASE)
        if match:
            mantissa = float(match.group(1))
            exponent = int(match.group(2))
            concentration = mantissa * (10 ** exponent)
            logger.info(f"Extracted concentration (E-notation): {mantissa}E{exponent} = {concentration:.2e}")
            return concentration, "e_notation"
        
        # Try plain number with unit
        match = re.search(self.PATTERNS['concentration_plain'], text, re.IGNORECASE)
        if match:
            concentration = float(match.group(1))
            logger.info(f"Extracted concentration (plain): {concentration:.2e}")
            return concentration, "plain"
        
        logger.warning("Could not extract concentration from PDF")
        return None, "not_found"
    
    def _extract_dilution(self, text: str) -> Optional[int]:
        """
        Extract dilution factor from text.
        
        Args:
            text: Full PDF text
            
        Returns:
            Dilution factor as integer, or None
        """
        # Try standard pattern: "Dilution factor: 500" or "Dilution: x500"
        match = re.search(self.PATTERNS['dilution'], text, re.IGNORECASE)
        if match:
            dilution = int(match.group(1))
            logger.info(f"Extracted dilution factor: {dilution}")
            return dilution
        
        # Try alternative pattern: "Diluted 500:1"
        match = re.search(self.PATTERNS['dilution_alt'], text, re.IGNORECASE)
        if match:
            dilution = int(match.group(1))
            logger.info(f"Extracted dilution factor (alt): {dilution}")
            return dilution
        
        logger.warning("Could not extract dilution factor from PDF")
        return None
    
    def parse(self) -> NTAPDFData:
        """
        Parse PDF and extract all available data.
        
        Returns:
            NTAPDFData object with extracted values
        """
        data = NTAPDFData(pdf_file_name=self.pdf_path.name)
        
        # Validate and extract text
        if not self.validate():
            data.extraction_errors.append("PDF validation failed")
            return data
            
        if not self._extract_text():
            data.extraction_errors.append("Text extraction failed")
            return data
        
        text = self.raw_text
        
        # Extract concentration
        concentration, method = self._extract_concentration(text)
        if concentration:
            data.original_concentration = concentration
        else:
            data.extraction_errors.append("Concentration not found")
        
        # Extract dilution
        dilution = self._extract_dilution(text)
        if dilution:
            data.dilution_factor = dilution
        else:
            data.extraction_errors.append("Dilution factor not found")
        
        # Calculate true population
        if data.original_concentration and data.dilution_factor:
            data.true_particle_population = data.original_concentration * data.dilution_factor
            logger.info(f"True particle population: {data.true_particle_population:.2e}")
        
        # Extract size statistics
        mean_size = self._extract_value(self.PATTERNS['mean_size'], text)
        if mean_size:
            data.mean_size_nm = float(mean_size)
        
        mode_size = self._extract_value(self.PATTERNS['mode_size'], text)
        if mode_size:
            data.mode_size_nm = float(mode_size)
        
        median_size = self._extract_value(self.PATTERNS['median_size'], text)
        if median_size:
            data.median_size_nm = float(median_size)
        
        d10 = self._extract_value(self.PATTERNS['d10'], text)
        if d10:
            data.d10_nm = float(d10)
        
        d50 = self._extract_value(self.PATTERNS['d50'], text)
        if d50:
            data.d50_nm = float(d50)
        
        d90 = self._extract_value(self.PATTERNS['d90'], text)
        if d90:
            data.d90_nm = float(d90)
        
        # Extract sample info
        sample_name = self._extract_value(self.PATTERNS['sample_name'], text)
        if sample_name:
            data.sample_name = sample_name.strip()
        
        date = self._extract_value(self.PATTERNS['date'], text)
        if date:
            data.measurement_date = date
        
        operator = self._extract_value(self.PATTERNS['operator'], text)
        if operator:
            data.operator = operator.strip()
        
        # Extract quality metrics
        frames = self._extract_value(self.PATTERNS['frames'], text)
        if frames:
            data.frames_analyzed = int(frames)
        
        duration = self._extract_value(self.PATTERNS['duration'], text)
        if duration:
            data.capture_duration_s = float(duration)
        
        # Check if extraction was successful
        data.extraction_successful = (
            data.original_concentration is not None or 
            data.dilution_factor is not None or
            data.mean_size_nm is not None
        )
        
        logger.success(f"PDF parsing complete: {data.extraction_successful}")
        return data
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Parse PDF and return results as dictionary.
        
        Returns:
            Dictionary with all extracted data
        """
        data = self.parse()
        return {
            'original_concentration': data.original_concentration,
            'dilution_factor': data.dilution_factor,
            'true_particle_population': data.true_particle_population,
            'mean_size_nm': data.mean_size_nm,
            'mode_size_nm': data.mode_size_nm,
            'median_size_nm': data.median_size_nm,
            'd10_nm': data.d10_nm,
            'd50_nm': data.d50_nm,
            'd90_nm': data.d90_nm,
            'sample_name': data.sample_name,
            'measurement_date': data.measurement_date,
            'operator': data.operator,
            'instrument': data.instrument,
            'frames_analyzed': data.frames_analyzed,
            'capture_duration_s': data.capture_duration_s,
            'pdf_file_name': data.pdf_file_name,
            'extraction_successful': data.extraction_successful,
            'extraction_errors': data.extraction_errors,
        }


# Convenience function for direct parsing
def parse_nta_pdf(pdf_path: Path) -> Dict[str, Any]:
    """
    Parse NTA PDF report and return extracted data.
    
    Args:
        pdf_path: Path to PDF file
        
    Returns:
        Dictionary with extracted concentration, dilution, and size data
    """
    parser = NTAPDFParser(pdf_path)
    return parser.to_dict()


# Check if PDF support is available
def check_pdf_support() -> bool:
    """Check if PDF parsing is available."""
    return PDF_SUPPORT
