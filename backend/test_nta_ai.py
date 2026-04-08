"""
NTA AI Analysis - Test Script
==============================

Tests all NTA AI endpoints we built:
1. Health check (AWS Bedrock connectivity)
2. Upload NTA files
3. AI Analysis (anomaly detection + missed parameters)
4. Metadata comparison across files

Usage:
    cd ~/biovaram/backend
    source venv/bin/activate
    python3 test_nta_ai.py

Make sure the backend is running first:
    python3 run_api.py
"""

import requests
import json
import os
from pathlib import Path

# ============================================================================
# Config
# ============================================================================

BASE_URL = "http://localhost:8000/api/v1"

# NTA files with actual particle data (detected particles > 0)
NTA_FILES_DIR = Path(__file__).parent / "NTA/EV_IPSC_P1_19_2_25_NTA"

GOOD_FILES = [
    "20250219_0002_EV_ip_p1_F8-1000_size_488.txt",   # 514 particles
    "20250219_0004_EV_ip_p1_F7-1000_size_488.txt",   # 346 particles
    "20250219_0011_EV_ip_p1_F9-5000_size_488.txt",   # 379 particles
]


def print_section(title: str):
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def print_result(label: str, data: dict):
    print(f"\n✅ {label}:")
    print(json.dumps(data, indent=2))


def print_error(label: str, error: str):
    print(f"\n❌ {label}: {error}")


# ============================================================================
# Test 1: Health Check
# ============================================================================

def test_health():
    print_section("TEST 1: AWS Bedrock Health Check")
    try:
        r = requests.get(f"{BASE_URL}/ai/nta/health")
        data = r.json()
        if data.get("status") == "ok":
            print_result("Bedrock connected", data)
        else:
            print_error("Bedrock not connected", str(data))
        return data.get("status") == "ok"
    except Exception as e:
        print_error("Health check failed", str(e))
        return False


# ============================================================================
# Test 2: Upload NTA Files
# ============================================================================

def test_upload_files():
    print_section("TEST 2: Upload NTA Files")
    sample_ids = []

    for filename in GOOD_FILES:
        filepath = NTA_FILES_DIR / filename
        if not filepath.exists():
            print(f"⚠️  File not found: {filepath}")
            continue

        try:
            with open(filepath, "rb") as f:
                r = requests.post(
                    f"{BASE_URL}/upload/nta",
                    files={"file": (filename, f, "text/plain")},
                    data={"treatment": "CD81", "operator": "Charmi"}
                )
            data = r.json()

            if data.get("processing_status") == "completed":
                sample_id = data.get("sample_id")
                sample_ids.append(sample_id)
                print(f"\n✅ Uploaded: {filename}")
                print(f"   Sample ID: {sample_id}")
                print(f"   Mean size: {data.get('nta_results', {}).get('mean_size_nm', 'N/A')} nm")
                print(f"   Concentration: {data.get('nta_results', {}).get('concentration_particles_ml', 'N/A'):.2e} particles/mL")
            else:
                print(f"\n⚠️  Upload pending/failed: {filename}")
                print(f"   Status: {data.get('processing_status')}")

        except Exception as e:
            print_error(f"Upload failed for {filename}", str(e))

    return sample_ids


# ============================================================================
# Test 3: AI Analysis
# ============================================================================

def test_ai_analysis(sample_ids: list):
    print_section("TEST 3: AI Analysis (Anomaly Detection + Missed Parameters)")

    if not sample_ids:
        print("⚠️  No sample IDs available. Run upload test first.")
        return

    payload = {
        "experiment_description": "EV from IPSC passage 1, analyzing exosome fractions F7, F8, F9",
        "same_sample": True,
        "parameters_of_interest": ["50-80nm", "80-100nm"],
        "sample_ids": sample_ids[:1],  # Test with first sample
        "additional_notes": "Focusing on small exosomes only, checking for CD81 marker"
    }

    try:
        r = requests.post(
            f"{BASE_URL}/ai/nta/analyze",
            json=payload,
            timeout=60  # AI call can take time
        )
        print(f"\n🔍 Raw response: {r.text[:500]}")
        data = r.json()

        print(f"\n📊 Analyzed samples: {data.get('analyzed_samples')}")
        print(f"🕐 Analyzed at: {data.get('analyzed_at')}")

        print("\n🚨 ANOMALIES DETECTED:")
        for a in data.get("anomalies", []):
            print(f"   • {a}")

        print("\n🔍 MISSED PARAMETERS:")
        for m in data.get("missed_parameters", []):
            print(f"   • {m}")

        print("\n💡 SUGGESTIONS:")
        for s in data.get("suggestions", []):
            print(f"   • {s}")

        print(f"\n📝 SUMMARY:\n   {data.get('summary')}")

    except Exception as e:
        print_error("AI analysis failed", str(e))


# ============================================================================
# Test 4: Metadata Comparison
# ============================================================================

def test_metadata_compare(sample_ids: list):
    print_section("TEST 4: Metadata Comparison Across Files")

    if len(sample_ids) < 2:
        print("⚠️  Need at least 2 sample IDs for comparison.")
        return

    payload = {
        "sample_ids": sample_ids[:2]  # Compare first two samples
    }

    try:
        r = requests.post(
            f"{BASE_URL}/ai/nta/compare-metadata",
            json=payload
        )
        print(f"\n🔍 Raw response: {r.text[:500]}")
        data = r.json()

        print(f"\n📊 Compared samples: {data.get('compared_samples')}")

        mismatches = data.get("mismatches", [])
        if mismatches:
            print("\n⚠️  MISMATCHES FOUND:")
            for m in mismatches:
                print(f"\n   Field: {m['field']}")
                print(f"   Values: {m['values']}")
                print(f"   Difference: {m['difference']} (tolerance: ±{m['tolerance']})")
                print(f"   Severity: {m['severity'].upper()}")
                print(f"   Message: {m['message']}")
        else:
            print("\n✅ No mismatches found")

        print(f"\n✅ MATCHING FIELDS: {data.get('matching_fields')}")
        print(f"\n📋 RECOMMENDATION:\n   {data.get('recommendation')}")

    except Exception as e:
        print_error("Metadata comparison failed", str(e))

# ============================================================================
# Test 5: Multi-sample AI Analysis
# ============================================================================

def test_multi_sample_analysis(sample_ids: list):
    print_section("TEST 5: Multi-Sample AI Analysis")

    if len(sample_ids) < 2:
        print("⚠️  Need at least 2 sample IDs.")
        return

    payload = {
        "experiment_description": "Same IPSC sample split into multiple fractions, comparing F7, F8, F9",
        "same_sample": True,
        "parameters_of_interest": ["80-100nm", "100-120nm"],
        "sample_ids": sample_ids,
        "additional_notes": "Looking at typical exosome range, same biological sample"
    }

    try:
        r = requests.post(
            f"{BASE_URL}/ai/nta/analyze",
            json=payload,
            timeout=60
        )
        data = r.json()

        print(f"\n📊 Analyzed {len(data.get('analyzed_samples', []))} samples")

        print("\n🚨 ANOMALIES:")
        for a in data.get("anomalies", []):
            print(f"   • {a}")

        print("\n🔍 MISSED PARAMETERS:")
        for m in data.get("missed_parameters", []):
            print(f"   • {m}")

        print("\n💡 SUGGESTIONS:")
        for s in data.get("suggestions", []):
            print(f"   • {s}")

        print(f"\n📝 SUMMARY:\n   {data.get('summary')}")

    except Exception as e:
        print_error("Multi-sample analysis failed", str(e))


# ============================================================================
# Main
# ============================================================================

if __name__ == "__main__":
    print("\n🧪 NTA AI ANALYSIS - TEST SUITE")
    print("Make sure backend is running: python3 run_api.py")

    # Test 1: Health
    healthy = test_health()
    if not healthy:
        print("\n❌ Backend/Bedrock not available. Start the backend first.")
        exit(1)

    # Test 2: Upload files
    sample_ids = test_upload_files()

    if not sample_ids:
        print("\n❌ No files uploaded successfully. Check NTA file paths.")
        exit(1)

    print(f"\n✅ Successfully uploaded {len(sample_ids)} samples: {sample_ids}")

    # Test 3: Single sample AI analysis
    test_ai_analysis(sample_ids)

    # Test 4: Metadata comparison
    test_metadata_compare(sample_ids)

    # Test 5: Multi-sample AI analysis
    if len(sample_ids) > 1:
        test_multi_sample_analysis(sample_ids)

    print("\n" + "=" * 60)
    print("  ✅ ALL TESTS COMPLETE")
    print("=" * 60)
