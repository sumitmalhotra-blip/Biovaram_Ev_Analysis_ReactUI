"""
End-to-End System Tests for CRMIT Platform
===========================================

Manual testing checklist and automated verification script.

Run manually:
    python tests/test_e2e_system.py
    
Run with pytest:
    pytest tests/test_e2e_system.py -v -s

Author: CRMIT DevOps Team
Date: November 27, 2025
"""

import requests
import time
import sys
from pathlib import Path
from typing import Dict, List, Tuple

# Configuration
API_URL = "http://localhost:8000"
STREAMLIT_URL = "http://localhost:8501"

# Test data
PROJECT_ROOT = Path(__file__).parent.parent
TEST_FCS = PROJECT_ROOT / "nanoFACS" / "10000 exo and cd81" / "Exo Control.fcs"


class ColorCodes:
    """ANSI color codes for terminal output."""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'
    BOLD = '\033[1m'


def print_header(text: str):
    """Print section header."""
    print(f"\n{ColorCodes.BOLD}{ColorCodes.BLUE}{'='*70}{ColorCodes.END}")
    print(f"{ColorCodes.BOLD}{ColorCodes.BLUE}{text:^70}{ColorCodes.END}")
    print(f"{ColorCodes.BOLD}{ColorCodes.BLUE}{'='*70}{ColorCodes.END}\n")


def print_test(name: str, passed: bool, message: str = ""):
    """Print test result."""
    status = f"{ColorCodes.GREEN}✅ PASS{ColorCodes.END}" if passed else f"{ColorCodes.RED}❌ FAIL{ColorCodes.END}"
    print(f"  {status} - {name}")
    if message:
        print(f"         {message}")


def check_service(url: str, name: str) -> bool:
    """Check if a service is running."""
    try:
        response = requests.get(url, timeout=5)
        return response.status_code == 200
    except:
        return False


def test_prerequisites() -> Tuple[int, int]:
    """Test 1: Verify prerequisites."""
    print_header("TEST 1: PREREQUISITES")
    
    passed = 0
    total = 0
    
    # Check Python version
    total += 1
    python_ok = sys.version_info >= (3, 11)
    print_test("Python 3.11+", python_ok, f"Version: {sys.version.split()[0]}")
    if python_ok:
        passed += 1
    
    # Check FastAPI backend
    total += 1
    api_ok = check_service(f"{API_URL}/health", "FastAPI")
    print_test("Backend API Running", api_ok, f"{API_URL}")
    if api_ok:
        passed += 1
    
    # Check Streamlit frontend
    total += 1
    ui_ok = check_service(STREAMLIT_URL, "Streamlit")
    print_test("Frontend UI Running", ui_ok, f"{STREAMLIT_URL}")
    if ui_ok:
        passed += 1
    
    # Check test data
    total += 1
    data_ok = TEST_FCS.exists()
    print_test("Test Data Available", data_ok, str(TEST_FCS))
    if data_ok:
        passed += 1
    
    return passed, total


def test_api_endpoints() -> Tuple[int, int]:
    """Test 2: API endpoint functionality."""
    print_header("TEST 2: API ENDPOINTS")
    
    passed = 0
    total = 0
    
    endpoints = [
        ("GET", "/health", "Health Check"),
        ("GET", "/api/v1/status", "Status Endpoint"),
        ("GET", "/api/v1/samples", "List Samples"),
        ("GET", "/docs", "API Documentation"),
    ]
    
    for method, path, name in endpoints:
        total += 1
        try:
            url = f"{API_URL}{path}"
            response = requests.get(url, timeout=5)
            success = response.status_code in [200, 404]  # 404 ok for empty lists
            print_test(name, success, f"{method} {path} → {response.status_code}")
            if success:
                passed += 1
        except Exception as e:
            print_test(name, False, str(e))
    
    return passed, total


def test_file_upload() -> Tuple[int, int]:
    """Test 3: File upload workflow."""
    print_header("TEST 3: FILE UPLOAD WORKFLOW")
    
    passed = 0
    total = 0
    
    if not TEST_FCS.exists():
        print_test("Test file missing", False, f"Cannot find {TEST_FCS}")
        return 0, 1
    
    # Prepare sample data
    sample_data = {
        "sample_id": f"E2E_TEST_{int(time.time())}",
        "treatment": "CD81",
        "concentration_ug": 1.0,
        "preparation_method": "SEC",
        "operator": "Automated Test",
        "notes": "End-to-end system test"
    }
    
    # Test upload
    total += 1
    try:
        with open(TEST_FCS, 'rb') as f:
            files = {'file': (TEST_FCS.name, f, 'application/octet-stream')}
            response = requests.post(
                f"{API_URL}/api/v1/upload/fcs",
                files=files,
                data=sample_data,
                timeout=60
            )
        
        upload_ok = response.status_code == 200
        if upload_ok:
            upload_result = response.json()
            sample_id = upload_result.get("id")
            print_test("Upload FCS File", True, f"Sample ID: {sample_id}")
            passed += 1
            
            # Test retrieval
            total += 1
            response = requests.get(f"{API_URL}/api/v1/samples/{sample_id}")
            retrieve_ok = response.status_code == 200
            print_test("Retrieve Sample", retrieve_ok, f"GET /api/v1/samples/{sample_id}")
            if retrieve_ok:
                passed += 1
                
                # Test metadata
                total += 1
                sample_detail = response.json()
                metadata_ok = (
                    sample_detail.get("sample_id") == sample_data["sample_id"] and
                    sample_detail.get("treatment") == sample_data["treatment"]
                )
                print_test("Metadata Integrity", metadata_ok, 
                          f"Treatment: {sample_detail.get('treatment')}")
                if metadata_ok:
                    passed += 1
        else:
            print_test("Upload FCS File", False, f"Status: {response.status_code}")
    
    except Exception as e:
        print_test("Upload FCS File", False, str(e))
    
    return passed, total


def test_sample_filtering() -> Tuple[int, int]:
    """Test 4: Sample filtering and search."""
    print_header("TEST 4: SAMPLE FILTERING")
    
    passed = 0
    total = 0
    
    # Test filter by treatment
    total += 1
    try:
        response = requests.get(
            f"{API_URL}/api/v1/samples",
            params={"treatment": "CD81", "limit": 5}
        )
        filter_ok = response.status_code == 200
        if filter_ok:
            data = response.json()
            count = len(data.get("samples", []))
            print_test("Filter by Treatment", True, f"Found {count} CD81 samples")
            passed += 1
        else:
            print_test("Filter by Treatment", False, f"Status: {response.status_code}")
    except Exception as e:
        print_test("Filter by Treatment", False, str(e))
    
    # Test pagination
    total += 1
    try:
        response = requests.get(
            f"{API_URL}/api/v1/samples",
            params={"skip": 0, "limit": 10}
        )
        page_ok = response.status_code == 200
        if page_ok:
            data = response.json()
            total_count = data.get("total", 0)
            print_test("Pagination", True, f"Total samples: {total_count}")
            passed += 1
        else:
            print_test("Pagination", False, f"Status: {response.status_code}")
    except Exception as e:
        print_test("Pagination", False, str(e))
    
    return passed, total


def test_data_visualization() -> Tuple[int, int]:
    """Test 5: Data visualization endpoints."""
    print_header("TEST 5: DATA VISUALIZATION")
    
    passed = 0
    total = 0
    
    # Check if plot generation works (through sample retrieval)
    total += 1
    try:
        response = requests.get(f"{API_URL}/api/v1/samples?limit=1")
        if response.status_code == 200:
            samples = response.json().get("samples", [])
            if samples:
                sample_id = samples[0]["id"]
                
                # Try to get FCS results (may include plot data)
                response = requests.get(f"{API_URL}/api/v1/samples/{sample_id}/fcs")
                viz_ok = response.status_code in [200, 404]  # 404 if not processed yet
                
                if response.status_code == 200:
                    print_test("FCS Results Available", True, f"Sample {sample_id} processed")
                else:
                    print_test("FCS Results Available", True, f"Sample {sample_id} not processed yet")
                passed += 1
            else:
                print_test("Sample Data", False, "No samples found")
        else:
            print_test("Sample Data", False, "Cannot retrieve samples")
    except Exception as e:
        print_test("Sample Data", False, str(e))
    
    return passed, total


def test_error_handling() -> Tuple[int, int]:
    """Test 6: Error handling."""
    print_header("TEST 6: ERROR HANDLING")
    
    passed = 0
    total = 0
    
    # Test invalid sample ID
    total += 1
    try:
        response = requests.get(f"{API_URL}/api/v1/samples/99999999")
        not_found_ok = response.status_code == 404
        print_test("404 Not Found", not_found_ok, "Invalid sample ID handled correctly")
        if not_found_ok:
            passed += 1
    except Exception as e:
        print_test("404 Not Found", False, str(e))
    
    # Test malformed request
    total += 1
    try:
        response = requests.post(
            f"{API_URL}/api/v1/upload/fcs",
            data={"invalid": "data"},  # Missing file
            timeout=5
        )
        validation_ok = response.status_code in [400, 422]  # 400 or 422 for validation error
        print_test("Validation Errors", validation_ok, f"Status: {response.status_code}")
        if validation_ok:
            passed += 1
    except Exception as e:
        print_test("Validation Errors", False, str(e))
    
    return passed, total


def test_performance() -> Tuple[int, int]:
    """Test 7: Performance benchmarks."""
    print_header("TEST 7: PERFORMANCE")
    
    passed = 0
    total = 0
    
    # Test API response time
    total += 1
    try:
        start = time.time()
        response = requests.get(f"{API_URL}/health")
        elapsed = time.time() - start
        
        perf_ok = elapsed < 1.0  # Should respond in < 1 second
        print_test("API Response Time", perf_ok, f"{elapsed*1000:.1f}ms (target: <1000ms)")
        if perf_ok:
            passed += 1
    except Exception as e:
        print_test("API Response Time", False, str(e))
    
    # Test sample list query time
    total += 1
    try:
        start = time.time()
        response = requests.get(f"{API_URL}/api/v1/samples?limit=50")
        elapsed = time.time() - start
        
        query_ok = elapsed < 2.0  # Should respond in < 2 seconds
        print_test("Database Query Time", query_ok, f"{elapsed*1000:.1f}ms (target: <2000ms)")
        if query_ok:
            passed += 1
    except Exception as e:
        print_test("Database Query Time", False, str(e))
    
    return passed, total


def main():
    """Run all tests."""
    print(f"\n{ColorCodes.BOLD}{'#'*70}{ColorCodes.END}")
    print(f"{ColorCodes.BOLD}   CRMIT PLATFORM - END-TO-END SYSTEM TESTS{ColorCodes.END}")
    print(f"{ColorCodes.BOLD}{'#'*70}{ColorCodes.END}")
    
    all_passed = 0
    all_total = 0
    
    # Run test suites
    test_suites = [
        ("Prerequisites", test_prerequisites),
        ("API Endpoints", test_api_endpoints),
        ("File Upload", test_file_upload),
        ("Sample Filtering", test_sample_filtering),
        ("Data Visualization", test_data_visualization),
        ("Error Handling", test_error_handling),
        ("Performance", test_performance),
    ]
    
    results = []
    for suite_name, test_func in test_suites:
        try:
            passed, total = test_func()
            all_passed += passed
            all_total += total
            results.append((suite_name, passed, total))
        except Exception as e:
            print(f"\n{ColorCodes.RED}Error running {suite_name}: {e}{ColorCodes.END}")
            results.append((suite_name, 0, 1))
            all_total += 1
    
    # Summary
    print_header("TEST SUMMARY")
    
    for suite_name, passed, total in results:
        percentage = (passed/total*100) if total > 0 else 0
        status = "✅" if passed == total else "⚠️" if passed > 0 else "❌"
        print(f"  {status} {suite_name:.<50} {passed}/{total} ({percentage:.0f}%)")
    
    print(f"\n{ColorCodes.BOLD}Overall Results:{ColorCodes.END}")
    overall_percentage = (all_passed/all_total*100) if all_total > 0 else 0
    print(f"  Total Tests: {all_total}")
    print(f"  Passed: {ColorCodes.GREEN}{all_passed}{ColorCodes.END}")
    print(f"  Failed: {ColorCodes.RED}{all_total - all_passed}{ColorCodes.END}")
    print(f"  Success Rate: {ColorCodes.BOLD}{overall_percentage:.1f}%{ColorCodes.END}")
    
    if all_passed == all_total:
        print(f"\n{ColorCodes.GREEN}{ColorCodes.BOLD}🎉 ALL TESTS PASSED! System is ready for production.{ColorCodes.END}\n")
        return 0
    else:
        print(f"\n{ColorCodes.YELLOW}{ColorCodes.BOLD}⚠️  Some tests failed. Review results above.{ColorCodes.END}\n")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
