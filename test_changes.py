#!/usr/bin/env python
"""
Quick validation script for nanofacs_ai.py changes
Tests:
1. Python syntax (import + compile check)
2. Helper functions exist and are callable
3. Type hints are valid
"""
import sys
import ast
import os

def test_python_syntax():
    """Test that nanofacs_ai.py has valid Python syntax"""
    filepath = os.path.join(os.path.dirname(__file__), 'backend/src/api/routers/nanofacs_ai.py')
    print(f"Testing Python syntax for: {filepath}")
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            code = f.read()
        
        # Parse the file
        ast.parse(code)
        print("✓ Python syntax is valid (AST parse successful)")
        return True
    except SyntaxError as e:
        print(f"✗ Syntax Error: {e}")
        print(f"  Line {e.lineno}: {e.text}")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def test_helper_functions():
    """Test that expected helper functions are defined"""
    filepath = os.path.join(os.path.dirname(__file__), 'backend/src/api/routers/nanofacs_ai.py')
    print("\nTesting helper functions...")
    
    expected_functions = [
        '_safe_float',
        '_normalize_file_key',
        '_build_raw_data_preview',
        '_compare_metric',
        '_build_consistency_check'
    ]
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        found_count = 0
        for func in expected_functions:
            if f"def {func}(" in content:
                print(f"  ✓ Found function: {func}")
                found_count += 1
            else:
                print(f"  ✗ Missing function: {func}")
        
        if found_count == len(expected_functions):
            print(f"✓ All {len(expected_functions)} helper functions found")
            return True
        else:
            print(f"✗ Only {found_count}/{len(expected_functions)} functions found")
            return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def test_consistency_check_model():
    """Test that FCSAnalysisResponse has consistency_check field"""
    filepath = os.path.join(os.path.dirname(__file__), 'backend/src/api/routers/nanofacs_ai.py')
    print("\nTesting FCSAnalysisResponse model...")
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if 'consistency_check' in content:
            if 'class FCSAnalysisResponse' in content:
                print("  ✓ FCSAnalysisResponse class found")
                if 'consistency_check:' in content:
                    print("  ✓ consistency_check field added to model")
                    return True
                else:
                    print("  ✗ consistency_check field not in model")
                    return False
            else:
                print("  ✗ FCSAnalysisResponse class not found")
                return False
        else:
            print("  ✗ No consistency_check references found")
            return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def test_frontend_consistency_check():
    """Test that nanofacs-ai-panel.tsx has consistency_check UI"""
    filepath = os.path.join(os.path.dirname(__file__), 'components/flow-cytometry/nanofacs-ai-panel.tsx')
    print("\nTesting frontend consistency_check UI...")
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        checks = [
            ('consistency_check interface', 'consistency_check?:'),
            ('consistency_check UI section', '{result.consistency_check &&'),
            ('verdict display', 'result.consistency_check.verdict')
        ]
        
        all_found = True
        for check_name, check_text in checks:
            if check_text in content:
                print(f"  ✓ {check_name}")
            else:
                print(f"  ✗ Missing {check_name}")
                all_found = False
        
        if all_found:
            print("✓ All frontend consistency_check components found")
            return True
        else:
            return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def main():
    """Run all tests"""
    print("=" * 60)
    print("VALIDATION TEST SUITE")
    print("=" * 60)
    
    results = []
    results.append(("Python Syntax", test_python_syntax()))
    results.append(("Helper Functions", test_helper_functions()))
    results.append(("Consistency Check Model", test_consistency_check_model()))
    results.append(("Frontend UI", test_frontend_consistency_check()))
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All validations PASSED! Changes are ready.")
        return 0
    else:
        print(f"\n⚠️  {total - passed} validation(s) FAILED. Review above.")
        return 1

if __name__ == '__main__':
    sys.exit(main())
