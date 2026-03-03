"""
Bead Datasheet Parser
=====================

Parses Certificate of Analysis documents from bead manufacturers
(e.g., Beckman Coulter nanoViS) in PDF or CSV format.

Extracts:
- Kit identity (part number, lot, manufacturer, expiry)
- Bead RI
- Subcomponents (e.g., nanoViS Low, nanoViS High)
- Bead populations (label, diameter_nm, CV%, concentration)

Supports:
- PDF files (using pdfplumber to extract tables)
- CSV/TSV files (direct parsing)

Author: CRMIT Backend Team
Date: February 2026
"""

from pathlib import Path
from typing import Dict, Any, Optional, List
import re
from dataclasses import dataclass, field
from loguru import logger

try:
    import pdfplumber  # type: ignore[import-untyped]
    PDF_SUPPORT = True
except ImportError:
    pdfplumber = None  # type: ignore[assignment]
    PDF_SUPPORT = False
    logger.warning("pdfplumber not installed. PDF bead datasheet parsing disabled.")


@dataclass
class BeadPopulation:
    """Single bead population from a datasheet."""
    label: str = ""
    diameter_nm: float = 0.0
    diameter_um: float = 0.0
    cv_pct: float = 0.0
    spec_min_um: Optional[float] = None
    spec_max_um: Optional[float] = None
    concentration_particles_per_ml: Optional[float] = None
    subcomponent: str = ""  # e.g., "nanoViS Low" or "nanoViS High"


@dataclass
class BeadDatasheetData:
    """All data extracted from a bead Certificate of Analysis."""
    # Kit identity
    kit_part_number: str = ""
    product_name: str = ""
    lot_number: str = ""
    manufacturer: str = ""
    manufacture_date: str = ""
    expiration_date: str = ""
    storage_condition: str = ""
    
    # Material properties
    material: str = "polystyrene_latex"
    refractive_index: float = 1.591
    ri_wavelength_nm: float = 590.0
    nist_traceable: bool = False
    
    # Subcomponents and beads
    subcomponents: Dict[str, List[BeadPopulation]] = field(default_factory=dict)
    all_beads: List[BeadPopulation] = field(default_factory=list)
    
    # Parse metadata
    source_file: str = ""
    parse_warnings: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            "kit_part_number": self.kit_part_number,
            "product_name": self.product_name,
            "lot_number": self.lot_number,
            "manufacturer": self.manufacturer,
            "manufacture_date": self.manufacture_date,
            "expiration_date": self.expiration_date,
            "storage_condition": self.storage_condition,
            "material": self.material,
            "refractive_index": self.refractive_index,
            "ri_wavelength_nm": self.ri_wavelength_nm,
            "nist_traceable": self.nist_traceable,
            "subcomponents": {
                name: [
                    {
                        "label": b.label,
                        "diameter_nm": b.diameter_nm,
                        "diameter_um": b.diameter_um,
                        "cv_pct": b.cv_pct,
                        "spec_min_um": b.spec_min_um,
                        "spec_max_um": b.spec_max_um,
                        "concentration_particles_per_ml": b.concentration_particles_per_ml,
                        "subcomponent": b.subcomponent,
                    }
                    for b in beads
                ]
                for name, beads in self.subcomponents.items()
            },
            "all_beads": [
                {
                    "label": b.label,
                    "diameter_nm": b.diameter_nm,
                    "diameter_um": b.diameter_um,
                    "cv_pct": b.cv_pct,
                    "subcomponent": b.subcomponent,
                }
                for b in self.all_beads
            ],
            "n_beads_total": len(self.all_beads),
            "n_subcomponents": len(self.subcomponents),
            "source_file": self.source_file,
            "parse_warnings": self.parse_warnings,
        }


def _parse_concentration(text: str) -> Optional[float]:
    """Parse concentration like '2.78 x 108' or '2.78e8'."""
    text = text.strip().replace(",", "")
    # Pattern: 2.78 x 10-6 or 2.78 x 108
    m = re.search(r'([\d.]+)\s*[x×]\s*10[\-]?(\d+)', text)
    if m:
        mantissa = float(m.group(1))
        # Handle both '10-6' (negative) and '108' (positive)
        exp_str = m.group(2)
        # Check if there was a minus sign before the digits
        if '-' in text[text.find('10'):]:
            return mantissa * 10 ** (-int(exp_str))
        return mantissa * 10 ** int(exp_str)
    # Try scientific notation
    try:
        return float(text)
    except ValueError:
        return None


def _parse_diameter_um(text: str) -> Optional[float]:
    """Parse diameter value in µm, e.g., '0.04' or '40nm' -> 0.04."""
    text = text.strip().replace(",", "")
    if text.upper() == "N/A" or not text:
        return None
    # Remove µm or nm suffix
    text = re.sub(r'\s*(µm|um|nm)\s*$', '', text, flags=re.IGNORECASE)
    try:
        return float(text)
    except ValueError:
        return None


def _parse_cv(text: str) -> Optional[float]:
    """Parse CV% like '11.5%' or '11.5'."""
    text = text.strip().replace("%", "").replace(",", "")
    if text.upper() == "N/A" or not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _parse_spec_range(text: str) -> tuple[Optional[float], Optional[float]]:
    """Parse diameter specification range like '0.040 – 0.048'."""
    text = text.strip()
    if text.upper() == "N/A" or not text:
        return None, None
    # Try: 0.040 – 0.048 or 0.040-0.048
    m = re.match(r'([\d.]+)\s*[–\-]\s*([\d.]+)', text)
    if m:
        return float(m.group(1)), float(m.group(2))
    return None, None


def parse_csv_datasheet(file_path: str | Path, content: Optional[str] = None) -> BeadDatasheetData:
    """
    Parse a CSV/TSV bead Certificate of Analysis.
    
    This handles the real-world format from Beckman Coulter nanoViS datasheets,
    which have a complex layout with metadata rows, subcomponent headers, etc.
    
    Args:
        file_path: Path to the CSV/TSV file
        content: Optional pre-read file content (if already loaded)
    
    Returns:
        BeadDatasheetData with all extracted information
    """
    result = BeadDatasheetData()
    result.source_file = str(file_path)
    
    if content is None:
        path = Path(file_path)
        content = path.read_text(encoding="utf-8", errors="replace")
    
    lines = content.strip().split("\n")
    lines = [l.rstrip("\r") for l in lines]
    
    if not lines:
        result.parse_warnings.append("Empty file")
        return result
    
    # Detect delimiter
    first_data_line = lines[0]
    if "\t" in first_data_line:
        delimiter = "\t"
    elif ";" in first_data_line:
        delimiter = ";"
    else:
        delimiter = ","
    
    def split_row(line: str) -> List[str]:
        return [c.strip().strip('"').strip("'") for c in line.split(delimiter)]
    
    rows = [split_row(l) for l in lines]
    
    # --- Pass 1: Extract kit metadata from header rows ---
    current_subcomponent = ""
    bead_data_started = False
    
    for i, row in enumerate(rows):
        joined = " ".join(row).strip()
        joined_lower = joined.lower()
        
        # Certificate of Analysis header - skip
        if "certificate of analysis" in joined_lower:
            continue
        
        # Kit part number (e.g., "D03231")
        if not result.kit_part_number:
            for cell in row:
                m = re.match(r'^[A-Z]?\d{4,6}$', cell.strip())
                if m:
                    result.kit_part_number = cell.strip()
                    break
        
        # Product name
        if "nanovis" in joined_lower and ("sizing" in joined_lower or "nanoscale" in joined_lower):
            result.product_name = "nanoViS Nanoscale Sizing Standards"
        elif "megamix" in joined_lower:
            result.product_name = joined.strip()
        elif "spherotech" in joined_lower:
            result.product_name = joined.strip()
        elif "apogee" in joined_lower:
            result.product_name = joined.strip()
        
        # Lot number
        for cell in row:
            cell_s = cell.strip()
            m = re.match(r'^\d{6,}$', cell_s)
            if m and not result.lot_number:
                result.lot_number = cell_s
                break
        
        # Dates
        for cell in row:
            date_m = re.match(r'(\d{4}-\d{2}-\d{2})', cell.strip())
            if date_m:
                date_val = date_m.group(1)
                # Determine if manufacture or expiration
                row_text = " ".join(row).lower()
                if not result.manufacture_date:
                    result.manufacture_date = date_val
                elif not result.expiration_date:
                    result.expiration_date = date_val
        
        # Storage condition
        if "°c" in joined_lower or "°C" in joined:
            m = re.search(r'(\d+°?\s*to\s*\d+°?\s*C)', joined, re.IGNORECASE)
            if m:
                result.storage_condition = m.group(1)
        
        # Refractive index
        for cell in row:
            cell_stripped = cell.strip()
            try:
                val = float(cell_stripped)
                if 1.45 <= val <= 1.65 and "refractive" in joined_lower or cell_stripped == "1.591":
                    result.refractive_index = val
            except ValueError:
                pass
        
        # NIST traceable
        if "nist" in joined_lower and ("traceable" in joined_lower or "standards" in joined_lower):
            result.nist_traceable = True
        
        # Manufacturer
        if "beckman" in joined_lower:
            result.manufacturer = "Beckman Coulter, Inc."
        
        # --- Pass 2: Detect subcomponent headers and bead rows ---
        # Subcomponent headers: "nanoViS Low", "nanoViS High"
        for cell in row:
            cell_stripped = cell.strip()
            if re.match(r'nanoViS\s+(Low|High)', cell_stripped, re.IGNORECASE):
                current_subcomponent = cell_stripped
                if current_subcomponent not in result.subcomponents:
                    result.subcomponents[current_subcomponent] = []
                break
        
        # Bead data rows: look for rows with a size label like " 44nm", " 80nm", etc.
        # or rows where column 2 (Mean Diameter) has a numeric value
        size_label_match = None
        for cell in row:
            cell_stripped = cell.strip()
            m = re.match(r'^(\d+)\s*nm$', cell_stripped, re.IGNORECASE)
            if m:
                size_label_match = cell_stripped
                break
        
        if size_label_match or (len(row) >= 3 and row[2].strip() and _parse_diameter_um(row[2]) is not None and row[2].strip().upper() != "N/A"):
            # This looks like a bead data row
            mean_diam_um = _parse_diameter_um(row[2]) if len(row) > 2 else None
            
            if mean_diam_um and mean_diam_um > 0:
                bead = BeadPopulation()
                bead.label = size_label_match or f"{int(mean_diam_um * 1000)}nm"
                bead.diameter_um = mean_diam_um
                bead.diameter_nm = round(mean_diam_um * 1000, 1)
                bead.subcomponent = current_subcomponent
                
                # Parse spec range (column 3)
                if len(row) > 3:
                    spec_min, spec_max = _parse_spec_range(row[3])
                    bead.spec_min_um = spec_min
                    bead.spec_max_um = spec_max
                
                # Parse CV% (column 4)
                if len(row) > 4:
                    cv = _parse_cv(row[4])
                    if cv is not None:
                        bead.cv_pct = cv
                
                # Parse concentration (column 6 - particles/mL)
                if len(row) > 6:
                    conc = _parse_concentration(row[6])
                    if conc is not None:
                        bead.concentration_particles_per_ml = conc
                
                # Check for RI in the row (column 7)
                if len(row) > 7:
                    try:
                        ri_val = float(row[7].strip())
                        if 1.4 <= ri_val <= 1.7:
                            result.refractive_index = ri_val
                    except (ValueError, IndexError):
                        pass
                
                result.all_beads.append(bead)
                if current_subcomponent and current_subcomponent in result.subcomponents:
                    result.subcomponents[current_subcomponent].append(bead)
    
    # Set defaults if not found
    if not result.product_name and result.kit_part_number:
        result.product_name = f"Bead Kit {result.kit_part_number}"
    if not result.material:
        result.material = "polystyrene_latex"
    
    # Validation
    if not result.all_beads:
        result.parse_warnings.append("No bead populations found in file")
    else:
        logger.info(f"Parsed {len(result.all_beads)} bead populations from {file_path}")
        for sub, beads in result.subcomponents.items():
            logger.info(f"  {sub}: {[b.label for b in beads]}")
    
    return result


def parse_pdf_datasheet(file_path: str | Path, content_bytes: Optional[bytes] = None) -> BeadDatasheetData:
    """
    Parse a PDF bead Certificate of Analysis using pdfplumber.
    
    Extracts tables and text from each page and applies the same
    parsing logic as the CSV parser.
    
    Args:
        file_path: Path to the PDF file
        content_bytes: Optional pre-read bytes (if file is in memory)
    
    Returns:
        BeadDatasheetData with all extracted information
    """
    if not PDF_SUPPORT:
        data = BeadDatasheetData()
        data.parse_warnings.append("pdfplumber not installed. Cannot parse PDF bead datasheets.")
        return data
    
    result = BeadDatasheetData()
    result.source_file = str(file_path)
    
    try:
        if content_bytes:
            import io
            pdf = pdfplumber.open(io.BytesIO(content_bytes))
        else:
            pdf = pdfplumber.open(str(file_path))
        
        all_text_lines = []
        
        for page in pdf.pages:
            # Try to extract tables first (more structured)
            tables = page.extract_tables()
            if tables:
                for table in tables:
                    for row in table:
                        if row:
                            # Clean up None cells
                            cleaned = [str(cell).strip() if cell else "" for cell in row]
                            all_text_lines.append(",".join(cleaned))
            else:
                # Fall back to text extraction
                text = page.extract_text()
                if text:
                    all_text_lines.extend(text.split("\n"))
        
        pdf.close()
        
        # Re-parse using the CSV parser with the extracted text
        csv_content = "\n".join(all_text_lines)
        result = parse_csv_datasheet(file_path, content=csv_content)
        
    except Exception as e:
        logger.error(f"Failed to parse PDF bead datasheet: {e}", exc_info=True)
        result.parse_warnings.append(f"PDF parse error: {str(e)}")
    
    return result


def parse_bead_datasheet(file_path: str | Path, content: Optional[bytes] = None) -> BeadDatasheetData:
    """
    Auto-detect file type and parse bead datasheet.
    
    Args:
        file_path: Path to file (used for extension detection)
        content: Optional raw file bytes
    
    Returns:
        BeadDatasheetData
    """
    path = Path(file_path)
    ext = path.suffix.lower()
    
    if ext == ".pdf":
        return parse_pdf_datasheet(file_path, content_bytes=content)
    elif ext in (".csv", ".tsv", ".txt"):
        text_content = content.decode("utf-8", errors="replace") if content else None
        return parse_csv_datasheet(file_path, content=text_content)
    else:
        data = BeadDatasheetData()
        data.parse_warnings.append(f"Unsupported file type: {ext}. Use PDF, CSV, or TSV.")
        return data
