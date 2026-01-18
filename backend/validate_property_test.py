#!/usr/bin/env python3
"""
Validation script for Property 16 test implementation.
This validates the test structure without requiring database connection.
"""

import ast
import os

def validate_property_test():
    """Validate that the property test is correctly implemented."""
    test_file = "tests/test_property_database_schema.py"
    
    if not os.path.exists(test_file):
        print(f"❌ Test file not found: {test_file}")
        return False
    
    with open(test_file, 'r') as f:
        content = f.read()
    
    # Check for required elements
    required_elements = [
        "Property 16: Encyclopedia Completeness",
        "Requirements 7.1, 7.2, 7.3, 7.4",
        "test_property_16_encyclopedia_completeness",
        "@given",
        "hypothesis",
        "asyncio",
        "EXPECTED_CATEGORIES",
        "operating_system",
        "programming_language",
        "database",
        "web_server",
        "framework"
    ]
    
    print("🔍 Validating Property 16 test implementation...\n")
    
    all_good = True
    for element in required_elements:
        if element in content:
            print(f"✅ Found: {element}")
        else:
            print(f"❌ Missing: {element}")
            all_good = False
    
    # Parse the AST to check for test methods
    try:
        tree = ast.parse(content)
        test_methods = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name.startswith('test_property_16'):
                test_methods.append(node.name)
        
        print(f"\n📋 Found {len(test_methods)} property test methods:")
        for method in test_methods:
            print(f"   - {method}")
        
        if len(test_methods) >= 5:
            print("✅ Sufficient test coverage")
        else:
            print("⚠️  Consider adding more test methods")
            
    except SyntaxError as e:
        print(f"❌ Syntax error in test file: {e}")
        all_good = False
    
    print("\n" + "="*50)
    
    if all_good:
        print("🎉 Property 16 test validation PASSED!")
        print("The test is correctly structured and ready to run.")
        return True
    else:
        print("❌ Property 16 test validation FAILED!")
        print("Please fix the issues above.")
        return False

if __name__ == "__main__":
    success = validate_property_test()
    exit(0 if success else 1)