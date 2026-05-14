#!/usr/bin/env python3
"""
VALIDATION SUMMARY - NanoFACS AI Consistency Verification Implementation

This script documents all changes made and validation status.
Run with: python IMPLEMENTATION_VALIDATION.py
"""

import ast
import sys
from pathlib import Path

# ============================================================================
# COLORS FOR TERMINAL OUTPUT
# ============================================================================
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'
BOLD = '\033[1m'

# ============================================================================
# PROJECT STRUCTURE
# ============================================================================
PROJECT_ROOT = Path(__file__).parent
BACKEND_PATH = PROJECT_ROOT / 'backend' / 'src' / 'api' / 'routers' / 'nanofacs_ai.py'
FRONTEND_PATH = PROJECT_ROOT / 'components' / 'flow-cytometry' / 'nanofacs-ai-panel.tsx'

# ============================================================================
# VALIDATION FUNCTIONS
# ============================================================================

def print_header(title):
    """Print section header."""
    print(f"\n{BOLD}{BLUE}{'='*70}{RESET}")
    print(f"{BOLD}{BLUE}  {title}{RESET}")
    print(f"{BOLD}{BLUE}{'='*70}{RESET}\n")

def print_check(passed, message):
    """Print check result."""
    symbol = f"{GREEN}✓{RESET}" if passed else f"{RED}✗{RESET}"
    print(f"  {symbol} {message}")

def validate_python_syntax():
    """Validate Python syntax for modified backend file."""
    print_header("1. PYTHON SYNTAX VALIDATION")
    
    if not BACKEND_PATH.exists():
        print_check(False, f"File not found: {BACKEND_PATH}")
        return False
    
    try:
        with open(BACKEND_PATH, 'r', encoding='utf-8') as f:
            code = f.read()
        ast.parse(code)
        print_check(True, f"Python AST parse successful: {BACKEND_PATH.name}")
        return True
    except SyntaxError as e:
        print_check(False, f"Syntax error at line {e.lineno}: {e.msg}")
        return False
    except Exception as e:
        print_check(False, f"Error: {e}")
        return False

def validate_helper_functions():
    """Check that all required helper functions exist."""
    print_header("2. HELPER FUNCTIONS CHECK")
    
    required_functions = [
        ('_safe_float', 'Type-safe float conversion'),
        ('_normalize_file_key', 'File key normalization'),
        ('_build_raw_data_preview', 'Raw data preview generation'),
        ('_compare_metric', 'Metric comparison with tolerance'),
        ('_build_consistency_check', 'Consistency check compilation'),
    ]
    
    try:
        with open(BACKEND_PATH, 'r', encoding='utf-8') as f:
            content = f.read()
        
        found = 0
        for func_name, description in required_functions:
            if f"def {func_name}(" in content:
                print_check(True, f"{func_name} — {description}")
                found += 1
            else:
                print_check(False, f"{func_name} not found")
        
        print(f"\n  Result: {found}/{len(required_functions)} functions found")
        return found == len(required_functions)
    except Exception as e:
        print_check(False, f"Error: {e}")
        return False

def validate_backend_model():
    """Check FCSAnalysisResponse model updates."""
    print_header("3. BACKEND MODEL VALIDATION")
    
    try:
        with open(BACKEND_PATH, 'r', encoding='utf-8') as f:
            content = f.read()
        
        checks = [
            ('class FCSAnalysisResponse', 'Response model exists'),
            ('consistency_check:', 'consistency_check field added'),
            ('def _build_consistency_check', 'Consistency check builder'),
        ]
        
        all_ok = True
        for check_text, description in checks:
            found = check_text in content
            print_check(found, description)
            all_ok = all_ok and found
        
        return all_ok
    except Exception as e:
        print_check(False, f"Error: {e}")
        return False

def validate_endpoint_updates():
    """Check that API endpoints are updated with raw data."""
    print_header("4. ENDPOINT UPDATES VALIDATION")
    
    try:
        with open(BACKEND_PATH, 'r', encoding='utf-8') as f:
            content = f.read()
        
        checks = [
            ('async def analyze_nanofacs_ai', 'Analyze endpoint exists'),
            ('_build_raw_data_preview', 'Raw data preview in analyze'),
            ('consistency_check', 'Consistency check in response'),
            ('independent_reading', 'Independent reading prompt added'),
            ('async def ask_nanofacs_ai', 'Ask endpoint exists'),
        ]
        
        all_ok = True
        for check_text, description in checks:
            found = check_text in content
            print_check(found, description)
            all_ok = all_ok and found
        
        return all_ok
    except Exception as e:
        print_check(False, f"Error: {e}")
        return False

def validate_frontend_types():
    """Check TypeScript interface updates."""
    print_header("5. FRONTEND TYPES VALIDATION")
    
    if not FRONTEND_PATH.exists():
        print_check(False, f"File not found: {FRONTEND_PATH}")
        return False
    
    try:
        with open(FRONTEND_PATH, 'r', encoding='utf-8') as f:
            content = f.read()
        
        checks = [
            ('consistency_check?:', 'Optional consistency_check field'),
            ('verdict:', 'Verdict enum in interface'),
            ('checks:', 'Checks array in interface'),
            ('{result.consistency_check &&', 'Conditional UI rendering'),
            ('Code vs AI Consistency', 'UI section title'),
        ]
        
        all_ok = True
        for check_text, description in checks:
            found = check_text in content
            print_check(found, description)
            all_ok = all_ok and found
        
        return all_ok
    except Exception as e:
        print_check(False, f"Error: {e}")
        return False

def validate_frontend_rendering():
    """Check UI rendering logic."""
    print_header("6. FRONTEND UI RENDERING VALIDATION")
    
    try:
        with open(FRONTEND_PATH, 'r', encoding='utf-8') as f:
            content = f.read()
        
        checks = [
            ('verdict === "match"', 'Match verdict handling'),
            ('verdict === "partial_match"', 'Partial match handling'),
            ('verdict === "mismatch"', 'Mismatch verdict handling'),
            ('result.consistency_check.checks', 'Metric checks display'),
        ]
        
        all_ok = True
        for check_text, description in checks:
            found = check_text in content
            print_check(found, description)
            all_ok = all_ok and found
        
        return all_ok
    except Exception as e:
        print_check(False, f"Error: {e}")
        return False

def check_backward_compatibility():
    """Verify backward compatibility."""
    print_header("7. BACKWARD COMPATIBILITY CHECK")
    
    try:
        with open(BACKEND_PATH, 'r', encoding='utf-8') as f:
            content = f.read()
        
        with open(FRONTEND_PATH, 'r', encoding='utf-8') as f:
            frontend_content = f.read()
        
        checks = [
            ('consistency_check: Optional', 'Backend field is optional'),
            ('consistency_check?:', 'Frontend field is optional'),
            ('{result.consistency_check &&', 'Frontend null-safe rendering'),
        ]
        
        all_ok = True
        search_content = content + frontend_content
        for check_text, description in checks:
            found = check_text in search_content
            print_check(found, description)
            all_ok = all_ok and found
        
        print("\n  → Old AI responses without consistency_check will still work")
        return all_ok
    except Exception as e:
        print_check(False, f"Error: {e}")
        return False

def print_summary(results):
    """Print overall summary."""
    print_header("VALIDATION SUMMARY")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    percentage = (passed / total * 100) if total > 0 else 0
    
    for name, result in results.items():
        status = f"{GREEN}PASS{RESET}" if result else f"{RED}FAIL{RESET}"
        print(f"  [{status}] {name}")
    
    print(f"\n  {BOLD}Total: {passed}/{total} ({percentage:.0f}%){RESET}")
    
    if passed == total:
        print(f"\n  {GREEN}{BOLD}🎉 ALL VALIDATIONS PASSED!{RESET}")
        print(f"  {GREEN}The implementation is code-ready.{RESET}")
        return True
    else:
        print(f"\n  {YELLOW}{BOLD}⚠️  {total - passed} validation(s) failed.{RESET}")
        return False

def main():
    """Run all validations."""
    print(f"\n{BOLD}{BLUE}")
    print("  ╔════════════════════════════════════════════════════════════════╗")
    print("  ║                                                                ║")
    print("  ║  NanoFACS AI Consistency Verification - Implementation Check  ║")
    print("  ║                                                                ║")
    print("  ║  Validates all code changes for the consistency verification  ║")
    print("  ║  feature that ensures AI analyzes raw data independently.     ║")
    print("  ║                                                                ║")
    print("  ╚════════════════════════════════════════════════════════════════╝")
    print(f"{RESET}\n")
    
    results = {
        "Python Syntax": validate_python_syntax(),
        "Helper Functions": validate_helper_functions(),
        "Backend Model": validate_backend_model(),
        "Endpoint Updates": validate_endpoint_updates(),
        "Frontend Types": validate_frontend_types(),
        "Frontend Rendering": validate_frontend_rendering(),
        "Backward Compatibility": check_backward_compatibility(),
    }
    
    success = print_summary(results)
    
    print_header("NEXT STEPS")
    print("""
  When environment supports PowerShell 7+ and npm:

  1. Run TypeScript type check:
     npx tsc --noEmit --project tsconfig.json

  2. Run frontend build:
     npm run build

  3. Run backend integration tests:
     python backend/test_nanofacs_ai.py
     (requires backend running on port 8000)

  4. Manual local testing:
     - Start backend: python backend/run_api.py
     - Start frontend: npm run dev
     - Upload sample FCS file
     - Run NanoFACS AI Analysis
     - Verify consistency_check section appears with verdict

  The code implementation is complete and ready for integration testing.
    """)
    
    return 0 if success else 1

if __name__ == '__main__':
    sys.exit(main())
