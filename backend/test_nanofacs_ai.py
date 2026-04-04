"""
NanoFACS AI Analysis - Test Script
=====================================

Tests all NanoFACS AI endpoints:
1. Health check (AWS Bedrock connectivity)
2. Single file AI analysis
3. Multi-file comparison
4. Q&A about data

Usage:
    cd ~/biovaram/backend
    source venv/bin/activate
    python3 test_nanofacs_ai.py

Make sure the backend is running first:
    python3 run_api.py

Also make sure you have extracted the PC3 zip file:
    unzip ~/Downloads/PC3-20260404T160138Z-1-001.zip -d /tmp/nanofacs_data/
"""

import requests
import json
import os
import zipfile
from pathlib import Path

# ============================================================================
# Config
# ============================================================================

BASE_URL = "http://localhost:8000/api/v1"

# Path where we extract parquet files for testing
EXTRACT_DIR = Path("/tmp/nanofacs_data")

# ZIP file locations — update if different on your machine
FCS_ZIP_FILES = [
    Path.home() / "Downloads/PC3-20260404T160138Z-1-001.zip",
    Path.home() / "Downloads/EV_HEK_TFF_DATA_05Dec25-20260404T160535Z-1-001.zip",
]


def print_section(title: str):
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def print_error(label: str, error: str):
    print(f"\n  ERROR - {label}: {error}")


# ============================================================================
# Setup — extract parquet files from zip
# ============================================================================

def setup_test_files() -> list[str]:
    """Extract FCS parquet files from zip archives."""
    print_section("SETUP: Extracting FCS Parquet Files")

    EXTRACT_DIR.mkdir(parents=True, exist_ok=True)
    fcs_parquet_files = []

    for zip_path in FCS_ZIP_FILES:
        if not zip_path.exists():
            print(f"  Zip not found: {zip_path}")
            continue

        try:
            with zipfile.ZipFile(zip_path, 'r') as z:
                # Only extract .fcs.parquet files (not txt or pdf)
                fcs_files = [f for f in z.namelist() if f.endswith('.fcs.parquet')]
                for f in fcs_files[:3]:  # take first 3 per zip
                    z.extract(f, EXTRACT_DIR)
                    full_path = str(EXTRACT_DIR / f)
                    fcs_parquet_files.append(full_path)
                    print(f"  Extracted: {f}")
        except Exception as e:
            print_error(f"Extract failed for {zip_path.name}", str(e))

    if not fcs_parquet_files:
        print("  No FCS parquet files found. Check zip file paths.")
    else:
        print(f"\n  Total FCS parquet files ready: {len(fcs_parquet_files)}")

    return fcs_parquet_files


# ============================================================================
# Test 1: Health Check
# ============================================================================

def test_health():
    print_section("TEST 1: AWS Bedrock Health Check")
    try:
        r = requests.get(f"{BASE_URL}/ai/nanofacs/health")
        data = r.json()
        if data.get("status") == "ok":
            print(f"\n  Bedrock connected")
            print(f"  Model: {data.get('model')}")
            print(f"  Region: {data.get('region')}")
        else:
            print_error("Bedrock not connected", str(data))
        return data.get("status") == "ok"
    except Exception as e:
        print_error("Health check failed", str(e))
        return False


# ============================================================================
# Test 2: Single File AI Analysis
# ============================================================================

def test_single_file_analysis(fcs_files: list[str]):
    print_section("TEST 2: Single File AI Analysis")

    if not fcs_files:
        print("  No FCS files available.")
        return

    payload = {
        "experiment_description": "PC3 cell line exosomes — checking EV size distribution and cluster patterns",
        "parameters_of_interest": ["Size", "MeanIntensity"],
        "same_sample": True,
        "additional_notes": "Looking at exosome fractions, interested in cluster behavior",
        "file_paths": [fcs_files[0]]
    }

    try:
        r = requests.post(
            f"{BASE_URL}/ai/nanofacs/analyze",
            json=payload,
            timeout=60
        )
        data = r.json()

        print(f"\n  Analyzed files: {data.get('analyzed_files')}")
        print(f"  Analyzed at: {data.get('analyzed_at')}")

        # Data stats summary
        stats = data.get("data_stats", {})
        for fname, fstats in stats.items():
            print(f"\n  File: {fname}")
            print(f"  Total events: {fstats.get('total_events')}")
            size = fstats.get("Size", {})
            if size:
                print(f"  Size — median: {size.get('median')}nm, mean: {size.get('mean')}nm")
            print(f"  Clusters: {fstats.get('num_clusters')}")

        print("\n  ANOMALIES DETECTED:")
        for a in data.get("anomalies", []):
            print(f"  - {a}")

        print("\n  CLUSTER FINDINGS:")
        for c in data.get("cluster_findings", []):
            print(f"  - {c}")

        print("\n  SUGGESTED GRAPHS:")
        for g in data.get("suggested_graphs", []):
            print(f"  - {g}")

        print("\n  MISSED PARAMETERS:")
        for m in data.get("missed_parameters", []):
            print(f"  - {m}")

        print("\n  SUGGESTIONS:")
        for s in data.get("suggestions", []):
            print(f"  - {s}")

        print(f"\n  SUMMARY:\n  {data.get('summary')}")

    except Exception as e:
        print_error("Single file analysis failed", str(e))


# ============================================================================
# Test 3: Multi-file Comparison
# ============================================================================

def test_multi_file_comparison(fcs_files: list[str]):
    print_section("TEST 3: Multi-File Comparison")

    if len(fcs_files) < 2:
        print("  Need at least 2 files for comparison.")
        return

    payload = {
        "file_paths": fcs_files[:3]
    }

    try:
        r = requests.post(
            f"{BASE_URL}/ai/nanofacs/compare",
            json=payload,
            timeout=60
        )
        data = r.json()

        print(f"\n  Compared files: {len(data.get('compared_files', []))} files")

        mismatches = data.get("mismatches", [])
        if mismatches:
            print("\n  MISMATCHES FOUND:")
            for m in mismatches:
                print(f"\n  Parameter: {m['parameter']}")
                print(f"  Values: {m['values']}")
                print(f"  Difference: {m['percent_difference']}%")
                print(f"  Severity: {m['severity'].upper()}")
                print(f"  Message: {m['message']}")
        else:
            print("\n  No significant mismatches found")

        print(f"\n  MATCHING FIELDS: {data.get('matching_fields')}")

        print("\n  CLUSTER COMPARISON:")
        for c in data.get("cluster_comparison", []):
            print(f"  - {c}")

        print(f"\n  RECOMMENDATION:\n  {data.get('recommendation')}")

    except Exception as e:
        print_error("Multi-file comparison failed", str(e))


# ============================================================================
# Test 4: Multi-file AI Analysis
# ============================================================================

def test_multi_file_analysis(fcs_files: list[str]):
    print_section("TEST 4: Multi-File AI Analysis")

    if len(fcs_files) < 2:
        print("  Need at least 2 files.")
        return

    payload = {
        "experiment_description": "PC3 and HEK cell line exosomes — comparing fractions",
        "parameters_of_interest": ["Size", "Cluster"],
        "same_sample": False,
        "additional_notes": "Different cell lines, checking for population differences",
        "file_paths": fcs_files[:3]
    }

    try:
        r = requests.post(
            f"{BASE_URL}/ai/nanofacs/analyze",
            json=payload,
            timeout=90
        )
        data = r.json()

        print(f"\n  Analyzed {len(data.get('analyzed_files', []))} files")

        print("\n  ANOMALIES:")
        for a in data.get("anomalies", []):
            print(f"  - {a}")

        print("\n  CLUSTER FINDINGS:")
        for c in data.get("cluster_findings", []):
            print(f"  - {c}")

        print("\n  SUGGESTED GRAPHS:")
        for g in data.get("suggested_graphs", []):
            print(f"  - {g}")

        print("\n  MISSED PARAMETERS:")
        for m in data.get("missed_parameters", []):
            print(f"  - {m}")

        print("\n  SUGGESTIONS:")
        for s in data.get("suggestions", []):
            print(f"  - {s}")

        print(f"\n  SUMMARY:\n  {data.get('summary')}")

    except Exception as e:
        print_error("Multi-file analysis failed", str(e))


# ============================================================================
# Test 5: Q&A about data
# ============================================================================

def test_ask_question(fcs_files: list[str]):
    print_section("TEST 5: Q&A About Data")

    if not fcs_files:
        print("  No FCS files available.")
        return

    questions = [
        "What is the median particle size and how does it compare to typical exosome range?",
        "Are there any unusual clusters in this data?",
        "Which size range has the most particles?",
    ]

    for question in questions:
        payload = {
            "question": question,
            "file_paths": [fcs_files[0]]
        }

        try:
            r = requests.post(
                f"{BASE_URL}/ai/nanofacs/ask",
                json=payload,
                timeout=30
            )
            data = r.json()

            print(f"\n  Q: {question}")
            print(f"  A: {data.get('answer')}")
            print(f"  Context: {data.get('data_context')}")

        except Exception as e:
            print_error(f"Q&A failed for '{question}'", str(e))


# ============================================================================
# Main
# ============================================================================

if __name__ == "__main__":
    print("\n  NANOFACS AI ANALYSIS - TEST SUITE")
    print("Make sure backend is running: python3 run_api.py")

    # Setup — extract files
    fcs_files = setup_test_files()

    # Test 1: Health
    healthy = test_health()
    if not healthy:
        print("\n  Backend/Bedrock not available. Start the backend first.")
        exit(1)

    if not fcs_files:
        print("\n  No FCS parquet files found. Check zip file paths in config.")
        exit(1)

    print(f"\n  Ready with {len(fcs_files)} FCS parquet files")

    # Test 2: Single file analysis
    test_single_file_analysis(fcs_files)

    # Test 3: Multi-file comparison
    if len(fcs_files) >= 2:
        test_multi_file_comparison(fcs_files)

    # Test 4: Multi-file AI analysis
    if len(fcs_files) >= 2:
        test_multi_file_analysis(fcs_files)

    # Test 5: Q&A
    test_ask_question(fcs_files)

    print("\n" + "=" * 60)
    print("  ALL TESTS COMPLETE")
    print("=" * 60)
