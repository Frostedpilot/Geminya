#!/usr/bin/env python3
"""
SUPER COMPLEX TEST SUITE RUNNER
Master test runner for all complex game system tests
Runs comprehensive testing scenarios based on Simple Waifu Game mechanics
"""

import sys
import os
import subprocess
import time
from datetime import datetime

def run_test_file(test_file: str, description: str):
    """Run a test file and return success status"""
    print(f"\n{'='*80}")
    print(f"🧪 RUNNING: {description}")
    print(f"📁 File: {test_file}")
    print(f"⏰ Started: {datetime.now().strftime('%H:%M:%S')}")
    print(f"{'='*80}")
    
    start_time = time.time()
    
    try:
        # Run the test file
        result = subprocess.run([sys.executable, test_file], 
                              capture_output=True, 
                              text=True, 
                              timeout=300)  # 5 minute timeout
        
        end_time = time.time()
        duration = end_time - start_time
        
        if result.returncode == 0:
            print(f"✅ PASSED ({duration:.2f}s)")
            print(f"📊 Output:\n{result.stdout}")
            return True
        else:
            print(f"❌ FAILED ({duration:.2f}s)")
            print(f"📊 Output:\n{result.stdout}")
            if result.stderr:
                print(f"🚨 Errors:\n{result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"⏰ TIMEOUT (300s)")
        return False
    except Exception as e:
        print(f"💥 EXCEPTION: {str(e)}")
        return False

def run_comprehensive_test_suite():
    """Run all complex test scenarios"""
    print("🌟 SUPER COMPLEX GAME SYSTEM TEST SUITE")
    print("="*90)
    print("Based on Simple Waifu Game Design Document")
    print("Testing edge cases, complex interactions, and system integration")
    print("="*90)
    
    # Define all test files and their descriptions
    test_files = [
        {
            "file": "test_unit_all_systems.py",
            "description": "Core Systems Unit Tests",
            "category": "Foundation",
            "priority": 1
        },
        {
            "file": "test_battle_full_system.py", 
            "description": "Full Battle Integration Test",
            "category": "Integration",
            "priority": 1
        },
        {
            "file": "test_complex_effect_resolution_fixed.py",
            "description": "Complex Effect Resolution & Status Interactions",
            "category": "Effects",
            "priority": 2
        },
        {
            "file": "test_battlefield_conditions.py",
            "description": "Battlefield Conditions & Environmental Effects",
            "category": "Environment", 
            "priority": 2
        },
        {
            "file": "test_edge_cases_fixed.py",
            "description": "Edge Cases & Extreme Scenarios",
            "category": "Edge Cases",
            "priority": 2
        },
        {
            "file": "test_ai_decisions.py",
            "description": "AI Decision Making & Target Selection",
            "category": "AI",
            "priority": 3
        },
        {
            "file": "test_signature_abilities.py",
            "description": "Signature Abilities & Special Mechanics",
            "category": "Special",
            "priority": 3
        }
    ]
    
    # Sort by priority
    test_files.sort(key=lambda x: x["priority"])
    
    # Track results
    results = {
        "passed": [],
        "failed": [],
        "skipped": []
    }
    
    # Display test plan
    print(f"\n📋 TEST EXECUTION PLAN")
    print(f"{'-'*60}")
    for i, test in enumerate(test_files, 1):
        status = "✓" if os.path.exists(test["file"]) else "✗ MISSING"
        print(f"{i:2d}. {test['description']:<45} [{test['category']}] {status}")
    
    print(f"\n🚀 STARTING TEST EXECUTION...")
    
    # Run each test file
    for i, test in enumerate(test_files, 1):
        print(f"\n🔄 Test {i}/{len(test_files)} - Priority {test['priority']}")
        
        if not os.path.exists(test["file"]):
            print(f"⚠️  SKIPPED: {test['file']} not found")
            results["skipped"].append(test)
            continue
        
        success = run_test_file(test["file"], test["description"])
        
        if success:
            results["passed"].append(test)
        else:
            results["failed"].append(test)
            
            # Check if this is a critical foundation test
            if test["priority"] == 1:
                print(f"\n🚨 CRITICAL TEST FAILED: {test['description']}")
                print("Foundation systems must pass before continuing with advanced tests")
                
                user_choice = input("Continue with remaining tests? (y/N): ").lower().strip()
                if user_choice != 'y':
                    print("Test execution halted due to critical failure")
                    break
        
        # Brief pause between tests
        time.sleep(1)
    
    # Generate comprehensive report
    generate_test_report(results, test_files)
    
    # Return overall success
    return len(results["failed"]) == 0

def generate_test_report(results, all_tests):
    """Generate a comprehensive test report"""
    total_tests = len(all_tests)
    passed_count = len(results["passed"])
    failed_count = len(results["failed"])
    skipped_count = len(results["skipped"])
    
    print(f"\n{'🏁 FINAL TEST REPORT':^80}")
    print(f"{'='*80}")
    
    # Summary statistics
    print(f"\n📊 SUMMARY STATISTICS")
    print(f"{'-'*40}")
    print(f"Total Tests:     {total_tests:3d}")
    print(f"Passed:          {passed_count:3d} ({passed_count/total_tests*100:.1f}%)")
    print(f"Failed:          {failed_count:3d} ({failed_count/total_tests*100:.1f}%)")
    print(f"Skipped:         {skipped_count:3d} ({skipped_count/total_tests*100:.1f}%)")
    
    # Detailed results by category
    categories = {}
    for test in all_tests:
        cat = test["category"]
        if cat not in categories:
            categories[cat] = {"total": 0, "passed": 0, "failed": 0, "skipped": 0}
        categories[cat]["total"] += 1
        
        if test in results["passed"]:
            categories[cat]["passed"] += 1
        elif test in results["failed"]:
            categories[cat]["failed"] += 1
        else:
            categories[cat]["skipped"] += 1
    
    print(f"\n📈 RESULTS BY CATEGORY")
    print(f"{'-'*60}")
    print(f"{'Category':<15} {'Total':<7} {'Passed':<7} {'Failed':<7} {'Skipped':<7}")
    print(f"{'-'*60}")
    
    for cat, stats in categories.items():
        print(f"{cat:<15} {stats['total']:<7} {stats['passed']:<7} {stats['failed']:<7} {stats['skipped']:<7}")
    
    # Failed tests details
    if results["failed"]:
        print(f"\n❌ FAILED TESTS")
        print(f"{'-'*40}")
        for test in results["failed"]:
            print(f"• {test['description']} [{test['category']}]")
    
    # Passed tests details
    if results["passed"]:
        print(f"\n✅ PASSED TESTS")
        print(f"{'-'*40}")
        for test in results["passed"]:
            print(f"• {test['description']} [{test['category']}]")
    
    # System coverage analysis
    print(f"\n🔍 SYSTEM COVERAGE ANALYSIS")
    print(f"{'-'*50}")
    
    systems_tested = {
        "Core Game Systems": passed_count >= 2,  # Unit + Integration tests
        "Status Effects": any(t["category"] == "Effects" for t in results["passed"]),
        "Environmental": any(t["category"] == "Environment" for t in results["passed"]),
        "Edge Cases": any(t["category"] == "Edge Cases" for t in results["passed"]),
        "AI Systems": any(t["category"] == "AI" for t in results["passed"]),
        "Special Mechanics": any(t["category"] == "Special" for t in results["passed"])
    }
    
    for system, covered in systems_tested.items():
        status = "✅ COVERED" if covered else "❌ NOT COVERED"
        print(f"{system:<20} {status}")
    
    # Overall assessment
    print(f"\n🎯 OVERALL ASSESSMENT")
    print(f"{'-'*40}")
    
    if failed_count == 0 and skipped_count == 0:
        grade = "EXCELLENT"
        message = "All systems fully tested and working perfectly!"
        emoji = "🌟"
    elif failed_count == 0:
        grade = "GOOD"
        message = "All executed tests passed, some tests skipped"
        emoji = "✨"
    elif failed_count <= 2:
        grade = "FAIR"
        message = "Most systems working, minor issues detected"
        emoji = "⚠️"
    else:
        grade = "POOR"
        message = "Multiple system failures detected"
        emoji = "🚨"
    
    print(f"{emoji} Grade: {grade}")
    print(f"Assessment: {message}")
    
    # Recommendations
    print(f"\n💡 RECOMMENDATIONS")
    print(f"{'-'*40}")
    
    if failed_count > 0:
        print("• Fix failed tests before production deployment")
        print("• Review error logs for critical issues")
    
    if skipped_count > 0:
        print("• Implement missing test files for complete coverage")
    
    if all(systems_tested.values()):
        print("• System is ready for advanced testing scenarios")
        print("• Consider stress testing and performance optimization")
    else:
        print("• Complete system coverage before advanced testing")
    
    print(f"\n🏆 Test suite execution completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*80}")

def main():
    """Main test runner function"""
    print("Starting Super Complex Test Suite...")
    
    # Change to script directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    try:
        success = run_comprehensive_test_suite()
        
        if success:
            print("\n🎉 ALL TESTS PASSED! Game systems are fully validated.")
            return 0
        else:
            print("\n💥 SOME TESTS FAILED! Review the report above.")
            return 1
            
    except KeyboardInterrupt:
        print("\n\n⚠️  Test execution interrupted by user")
        return 2
    except Exception as e:
        print(f"\n💥 Unexpected error during test execution: {e}")
        return 3

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
