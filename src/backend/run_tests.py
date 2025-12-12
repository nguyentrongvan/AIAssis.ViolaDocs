#!/usr/bin/env python
"""Quick test runner to check test results"""
import subprocess
import sys

def run_tests(test_file):
    """Run pytest for a specific test file"""
    result = subprocess.run(
        [sys.executable, "-m", "pytest", test_file, "-v", "--tb=short"],
        capture_output=True,
        text=True,
        cwd="."
    )
    print(f"\n{'='*60}")
    print(f"Testing: {test_file}")
    print(f"{'='*60}")
    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)
    print(f"Return code: {result.returncode}")
    return result.returncode == 0

if __name__ == "__main__":
    test_files = [
        "tests/test_utils_response.py",
        "tests/test_services_auth.py",
        "tests/test_services_storage.py",
        "tests/test_health.py",
        "tests/test_auth.py"
    ]
    
    results = {}
    for test_file in test_files:
        results[test_file] = run_tests(test_file)
    
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    for test_file, passed in results.items():
        status = "PASS" if passed else "FAIL"
        print(f"{status}: {test_file}")
    
    all_passed = all(results.values())
    sys.exit(0 if all_passed else 1)




