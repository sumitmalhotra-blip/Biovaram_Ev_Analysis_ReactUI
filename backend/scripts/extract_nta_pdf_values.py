"""
TASK-NTA-002: Extract Machine Report Values from PDF
=====================================================
This script extracts key metrics from ZetaView PDF reports and compares
them with our calculated values from TASK-NTA-001.

Created: January 20, 2026
"""

from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.parsers.nta_pdf_parser import NTAPDFParser, NTAPDFData
import json
import pandas as pd
import pdfplumber
import re


def extract_metrics_from_pdf_text(text: str, filename: str) -> dict:
    """
    Extract all available metrics from ZetaView PDF text.
    
    Based on actual PDF format analysis:
    - Sample Name: PC3_100kDa_F5
    - Median (X50) 127.3 127.3 218.9
    - Mean 143.8 143.8 265.4
    - StdDev 62.0 62.0 140.0
    - Concentration: 1.3E+7 Particles / mL
    - Original Concentration: 6.6E+9 Particles / mL
    - X10, X50, X90 values in "X Values" section
    """
    # Use Dict[str, Any] type to allow mixed value types
    result: dict = {
        'file': filename,
        'extraction_method': 'pdfplumber_zetaview',
    }
    
    # Extract Sample Name - format: "Sample Name: PC3_100kDa_F5"
    match = re.search(r'Sample Name:\s*(\S+)', text)
    if match:
        result['sample_name'] = match.group(1).strip()
    
    # Extract Concentration - format: "Concentration: 1.3E+7 Particles / mL"
    match = re.search(r'Concentration:\s*(\d+\.?\d*)[Ee]\+?(\d+)\s*Particles', text)
    if match:
        mantissa = float(match.group(1))
        exponent = int(match.group(2))
        result['concentration_particles_ml'] = mantissa * (10 ** exponent)
        result['concentration_str'] = f"{mantissa}E+{exponent}"
    
    # Extract Original Concentration - format: "Original Concentration: 6.6E+9 Particles / mL"
    match = re.search(r'Original Concentration:\s*(\d+\.?\d*)[Ee]\+?(\d+)\s*Particles', text)
    if match:
        mantissa = float(match.group(1))
        exponent = int(match.group(2))
        result['original_concentration_particles_ml'] = mantissa * (10 ** exponent)
        result['original_concentration_str'] = f"{mantissa}E+{exponent}"
    
    # Extract Dilution Factor - format: "Dilution Factor: 500"
    match = re.search(r'Dilution Factor:\s*(\d+)', text)
    if match:
        result['dilution'] = int(match.group(1))
    
    # Extract Mean - format in "X Values" section or standalone: "Mean 143.8 143.8 265.4"
    match = re.search(r'Mean\s+(\d+\.?\d*)\s+(\d+\.?\d*)\s+(\d+\.?\d*)', text)
    if match:
        result['mean_nm'] = float(match.group(1))  # Number-weighted mean
        result['mean_concentration_nm'] = float(match.group(2))  # Concentration-weighted
        result['mean_volume_nm'] = float(match.group(3))  # Volume-weighted
    
    # Extract Median (X50) - format: "Median (X50) 127.3 127.3 218.9" or "X50 127.3 127.3 218.9"
    match = re.search(r'(?:Median \(X50\)|X50)\s+(\d+\.?\d*)\s+(\d+\.?\d*)\s+(\d+\.?\d*)', text)
    if match:
        result['median_nm'] = float(match.group(1))  # Number-weighted median (D50)
        result['median_concentration_nm'] = float(match.group(2))
        result['median_volume_nm'] = float(match.group(3))
    
    # Extract StdDev - format: "StdDev 62.0 62.0 140.0"
    match = re.search(r'StdDev\s+(\d+\.?\d*)\s+(\d+\.?\d*)\s+(\d+\.?\d*)', text)
    if match:
        result['std_dev_nm'] = float(match.group(1))
    
    # Extract X10 - format: "X10 79.8 79.8 125.3"
    match = re.search(r'X10\s+(\d+\.?\d*)\s+(\d+\.?\d*)\s+(\d+\.?\d*)', text)
    if match:
        result['d10_nm'] = float(match.group(1))
    
    # Extract X90 - format: "X90 213.5 213.5 468.3"
    match = re.search(r'X90\s+(\d+\.?\d*)\s+(\d+\.?\d*)\s+(\d+\.?\d*)', text)
    if match:
        result['d90_nm'] = float(match.group(1))
    
    # Extract Span - format: "Span 1.1 1.1 1.6"
    match = re.search(r'Span\s+(\d+\.?\d*)', text)
    if match:
        result['span'] = float(match.group(1))
    
    # Extract Peak Analysis - format: "101.8 6.3E+5 89.4 100.0" (mode, concentration, FWHM, percentage)
    match = re.search(r'Peak Analysis.*?(\d+\.?\d*)\s+(\d+\.?\d*)[Ee]\+?(\d+)\s+(\d+\.?\d*)\s+(\d+\.?\d*)', text, re.DOTALL)
    if match:
        result['mode_nm'] = float(match.group(1))  # Peak diameter (mode)
        peak_conc_mantissa = float(match.group(2))
        peak_conc_exp = int(match.group(3))
        result['peak_concentration'] = peak_conc_mantissa * (10 ** peak_conc_exp)
        result['fwhm_nm'] = float(match.group(4))  # Full Width at Half Maximum
    
    # Extract Number of Traced Particles - format: "Number of Traced Particles: 630"
    match = re.search(r'Number of Traced Particles:\s*(\d+)', text)
    if match:
        result['traced_particles'] = int(match.group(1))
    
    # Extract Temperature - format: "Temperature: 25.13 °C"
    match = re.search(r'Temperature:\s*(\d+\.?\d*)\s*°C', text)
    if match:
        result['temperature_c'] = float(match.group(1))
    
    # Extract Laser Wavelength - format: "Laser Wavelength: 488 nm"
    match = re.search(r'Laser Wavelength:\s*(\d+)\s*nm', text)
    if match:
        result['laser_wavelength_nm'] = int(match.group(1))
    
    return result


def extract_from_pdf_tables(pdf_path: Path) -> dict:
    """
    Extract metrics from PDF tables (ZetaView often uses tables for stats).
    """
    # Use Dict[str, Any] type to allow mixed value types
    result: dict = {'file': pdf_path.name, 'extraction_method': 'pdfplumber_tables'}
    
    try:
        with pdfplumber.open(str(pdf_path)) as pdf:
            for page in pdf.pages:
                # Try to extract tables
                tables = page.extract_tables()
                for table in tables:
                    for row in table:
                        if row and len(row) >= 2:
                            label = str(row[0]).lower() if row[0] else ""
                            value = row[1] if len(row) > 1 else None
                            
                            if 'mean' in label and value:
                                try:
                                    mean_match = re.search(r'[\d.]+', str(value))
                                    if mean_match:
                                        result['mean_nm'] = float(mean_match.group())
                                except:
                                    pass
                            elif 'median' in label and value:
                                try:
                                    median_match = re.search(r'[\d.]+', str(value))
                                    if median_match:
                                        result['median_nm'] = float(median_match.group())
                                except:
                                    pass
                            elif 'mode' in label and value:
                                try:
                                    mode_match = re.search(r'[\d.]+', str(value))
                                    if mode_match:
                                        result['mode_nm'] = float(mode_match.group())
                                except:
                                    pass
    except Exception as e:
        result['error'] = str(e)
    
    return result


def parse_all_pdf_reports():
    """Parse all NTA PDF reports and extract machine values."""
    nta_dir = Path(__file__).parent.parent / 'NTA' / 'PC3'
    pdf_files = sorted(nta_dir.glob('*.pdf'))
    
    print("=" * 80)
    print("🔬 TASK-NTA-002: Extract Machine Report Values from PDF")
    print("=" * 80)
    print(f"\nFound {len(pdf_files)} PDF files in {nta_dir}\n")
    
    all_results = []
    
    for pdf_path in pdf_files:
        print(f"\n📄 Processing: {pdf_path.name}")
        print("-" * 60)
        
        try:
            # Extract full text
            with pdfplumber.open(str(pdf_path)) as pdf:
                full_text = ""
                for page in pdf.pages:
                    page_text = page.extract_text() or ""
                    full_text += page_text + "\n"
            
            # Show what we found in the PDF
            print(f"   Extracted {len(full_text)} characters from PDF")
            
            # Try text extraction
            result = extract_metrics_from_pdf_text(full_text, pdf_path.name)
            
            # Also try table extraction
            table_result = extract_from_pdf_tables(pdf_path)
            
            # Merge results (text takes precedence)
            for key, value in table_result.items():
                if key not in result or result[key] is None:
                    result[key] = value
            
            all_results.append(result)
            
            # Print extracted values
            print(f"   Sample Name: {result.get('sample_name', 'N/A')}")
            if 'concentration_particles_ml' in result:
                print(f"   Concentration: {result.get('concentration_str', 'N/A')} particles/mL")
            print(f"   Mean Size: {result.get('mean_nm', 'N/A')} nm")
            print(f"   Median Size: {result.get('median_nm', 'N/A')} nm")
            print(f"   Mode Size: {result.get('mode_nm', 'N/A')} nm")
            print(f"   D10: {result.get('d10_nm', 'N/A')} nm")
            print(f"   D50: {result.get('d50_nm', 'N/A')} nm")
            print(f"   D90: {result.get('d90_nm', 'N/A')} nm")
            print(f"   Dilution: {result.get('dilution', 'N/A')}x")
            
            # Debug: show first 1500 chars of text if extraction failed
            if 'concentration_particles_ml' not in result:
                print("\n   ⚠️  Concentration not found. PDF text preview:")
                print("   " + "-" * 50)
                preview = full_text[:1500].replace('\n', '\n   ')
                print(f"   {preview}")
                print("   " + "-" * 50)
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
            import traceback
            traceback.print_exc()
            all_results.append({'file': pdf_path.name, 'error': str(e)})
    
    return all_results


def compare_with_parsed_results(pdf_results: list):
    """Compare PDF machine values with our parsed values from TASK-NTA-001."""
    
    # Load our results from NTA-001
    validation_file = Path(__file__).parent.parent / 'data' / 'validation' / 'nta_pc3_parsed_results.json'
    
    if not validation_file.exists():
        print("\n⚠️  Cannot compare - run TASK-NTA-001 first!")
        return
    
    with open(validation_file, 'r') as f:
        our_results = json.load(f)
    
    print("\n" + "=" * 80)
    print("📊 COMPARISON: Machine PDF Values vs Our Calculated Values")
    print("=" * 80)
    
    # Create lookup by sample name
    our_lookup = {r['sample_name']: r for r in our_results}
    
    print("\n### Size Statistics Comparison ###")
    print("\n| Sample | Metric | Machine | Ours | Diff | % Error | Status |")
    print("|--------|--------|---------|------|------|---------|--------|")
    
    comparison_data = []
    
    for pdf_result in pdf_results:
        sample = pdf_result.get('sample_name', '').strip()
        
        if sample in our_lookup:
            our = our_lookup[sample]
            
            # Compare median (D50)
            if 'median_nm' in pdf_result and pdf_result['median_nm']:
                machine_median = pdf_result['median_nm']
                our_median = our['median_d50_nm']
                diff = our_median - machine_median
                pct = abs(diff / machine_median) * 100 if machine_median else 0
                status = "✅ PASS" if pct < 10 else "⚠️ CHECK"
                print(f"| {sample[:18]:18} | Median | {machine_median:7.1f} | {our_median:7.1f} | {diff:+6.1f} | {pct:5.1f}% | {status} |")
                comparison_data.append({
                    'sample': sample, 'metric': 'median_d50', 
                    'machine': machine_median, 'ours': our_median, 'pct_error': round(pct, 2)
                })
            
            # Compare mean
            if 'mean_nm' in pdf_result and pdf_result['mean_nm']:
                machine_mean = pdf_result['mean_nm']
                our_mean = our['mean_nm']
                diff = our_mean - machine_mean
                pct = abs(diff / machine_mean) * 100 if machine_mean else 0
                status = "✅ PASS" if pct < 10 else "⚠️ CHECK"
                print(f"| {sample[:18]:18} | Mean   | {machine_mean:7.1f} | {our_mean:7.1f} | {diff:+6.1f} | {pct:5.1f}% | {status} |")
                comparison_data.append({
                    'sample': sample, 'metric': 'mean', 
                    'machine': machine_mean, 'ours': our_mean, 'pct_error': round(pct, 2)
                })
            
            # Compare mode
            if 'mode_nm' in pdf_result and pdf_result['mode_nm']:
                machine_mode = pdf_result['mode_nm']
                our_mode = our['mode_nm']
                diff = our_mode - machine_mode
                pct = abs(diff / machine_mode) * 100 if machine_mode else 0
                status = "✅ PASS" if pct < 10 else "⚠️ CHECK"
                print(f"| {sample[:18]:18} | Mode   | {machine_mode:7.1f} | {our_mode:7.1f} | {diff:+6.1f} | {pct:5.1f}% | {status} |")
                comparison_data.append({
                    'sample': sample, 'metric': 'mode', 
                    'machine': machine_mode, 'ours': our_mode, 'pct_error': round(pct, 2)
                })
            
            # Compare D10
            if 'd10_nm' in pdf_result and pdf_result['d10_nm'] and 'd10_nm' in our:
                machine_d10 = pdf_result['d10_nm']
                our_d10 = our['d10_nm']
                diff = our_d10 - machine_d10
                pct = abs(diff / machine_d10) * 100 if machine_d10 else 0
                status = "✅ PASS" if pct < 10 else "⚠️ CHECK"
                print(f"| {sample[:18]:18} | D10    | {machine_d10:7.1f} | {our_d10:7.1f} | {diff:+6.1f} | {pct:5.1f}% | {status} |")
                comparison_data.append({
                    'sample': sample, 'metric': 'd10', 
                    'machine': machine_d10, 'ours': our_d10, 'pct_error': round(pct, 2)
                })
            
            # Compare D90
            if 'd90_nm' in pdf_result and pdf_result['d90_nm'] and 'd90_nm' in our:
                machine_d90 = pdf_result['d90_nm']
                our_d90 = our['d90_nm']
                diff = our_d90 - machine_d90
                pct = abs(diff / machine_d90) * 100 if machine_d90 else 0
                status = "✅ PASS" if pct < 10 else "⚠️ CHECK"
                print(f"| {sample[:18]:18} | D90    | {machine_d90:7.1f} | {our_d90:7.1f} | {diff:+6.1f} | {pct:5.1f}% | {status} |")
                comparison_data.append({
                    'sample': sample, 'metric': 'd90', 
                    'machine': machine_d90, 'ours': our_d90, 'pct_error': round(pct, 2)
                })
            
            # Compare StdDev
            if 'std_dev_nm' in pdf_result and pdf_result['std_dev_nm'] and 'std_nm' in our:
                machine_std = pdf_result['std_dev_nm']
                our_std = our['std_nm']
                diff = our_std - machine_std
                pct = abs(diff / machine_std) * 100 if machine_std else 0
                status = "✅ PASS" if pct < 10 else "⚠️ CHECK"
                print(f"| {sample[:18]:18} | StdDev | {machine_std:7.1f} | {our_std:7.1f} | {diff:+6.1f} | {pct:5.1f}% | {status} |")
                comparison_data.append({
                    'sample': sample, 'metric': 'std_dev', 
                    'machine': machine_std, 'ours': our_std, 'pct_error': round(pct, 2)
                })
            
            print("|" + "-" * 78 + "|")
    
    # Print summary
    if comparison_data:
        print("\n### Summary ###")
        passed = sum(1 for c in comparison_data if c['pct_error'] < 10)
        total = len(comparison_data)
        print(f"✅ Passed: {passed}/{total} comparisons ({100*passed/total:.0f}%)")
        
        # Average error by metric
        print("\n| Metric | Avg Error |")
        print("|--------|-----------|")
        metrics = set(c['metric'] for c in comparison_data)
        for metric in sorted(metrics):
            errors = [c['pct_error'] for c in comparison_data if c['metric'] == metric]
            avg_err = sum(errors) / len(errors) if errors else 0
            print(f"| {metric:10} | {avg_err:6.2f}% |")
    
    return comparison_data


def save_results(pdf_results: list, comparison_data: list):
    """Save PDF extraction results."""
    output_dir = Path(__file__).parent.parent / 'data' / 'validation'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save PDF results
    pdf_file = output_dir / 'nta_pc3_pdf_machine_values.json'
    with open(pdf_file, 'w') as f:
        json.dump(pdf_results, f, indent=2)
    print(f"\n💾 PDF results saved to: {pdf_file}")
    
    # Save comparison data
    if comparison_data:
        comp_file = output_dir / 'nta_pc3_comparison.json'
        with open(comp_file, 'w') as f:
            json.dump(comparison_data, f, indent=2)
        print(f"💾 Comparison saved to: {comp_file}")
        
        # Also as CSV
        df = pd.DataFrame(comparison_data)
        csv_file = output_dir / 'nta_pc3_comparison.csv'
        df.to_csv(csv_file, index=False)
        print(f"💾 Comparison CSV: {csv_file}")


if __name__ == '__main__':
    # Parse PDFs
    pdf_results = parse_all_pdf_reports()
    
    # Compare with our results
    comparison_data = compare_with_parsed_results(pdf_results)
    
    # Save everything
    save_results(pdf_results, comparison_data or [])
    
    print("\n✅ TASK-NTA-002 Complete!")
