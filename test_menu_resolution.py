#!/usr/bin/env python
"""
Simple test for menu resolution functionality
"""

import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Now import the specific module
from apps.triage.tools.conversational_intake_agent import STRUCTURED_MENUS, MenuResolver

def test_menu_resolution():
    """Test menu resolution without Django setup"""
    print("🧪 TESTING MENU RESOLUTION")
    print("=" * 50)
    
    # Test age_sex_gate menu
    print("\n📝 AGE/SEX GATE TESTS:")
    age_menu = STRUCTURED_MENUS["age_sex_gate"]
    
    test_cases = [
        ("1A", {"age_group": "newborn", "sex": "male"}),
        ("1B", {"age_group": "newborn", "sex": "female"}),
        ("3A", {"age_group": "child_1_5", "sex": "male"}),
        ("6B", {"age_group": "adult", "sex": "female"}),
        ("7A", {"age_group": "elderly", "sex": "male"}),
        ("7B", {"age_group": "elderly", "sex": "female"}),
        ("invalid", None),
    ]
    
    for input_val, expected in test_cases:
        print(f"  Input: '{input_val}' -> Expected: {expected}")
        
        matched, result = MenuResolver.resolve("age_sex_gate", input_val)
        
        if matched:
            if result == expected:
                print(f"  ✅ CORRECT: {result}")
            else:
                print(f"  ❌ INCORRECT: Expected {expected}, got {result}")
        else:
            print(f"  ❌ NOT RESOLVED: Input '{input_val}' not recognized")
    
    # Test pregnancy_status menu
    print("\n🤰 PREGNANCY STATUS TESTS:")
    pregnancy_menu = STRUCTURED_MENUS["pregnancy_status"]
    
    pregnancy_tests = [
        ("1", "yes"),
        ("2", "no"), 
        ("3", "not_sure"),
        ("yes", "yes"),
        ("no", "no"),
        ("invalid", None),
    ]
    
    for input_val, expected in pregnancy_tests:
        print(f"  Input: '{input_val}' -> Expected: {expected}")
        
        matched, result = MenuResolver.resolve("pregnancy_status", input_val)
        
        if matched:
            if result == expected:
                print(f"  ✅ CORRECT: {result}")
            else:
                print(f"  ❌ INCORRECT: Expected {expected}, got {result}")
        else:
            print(f"  ❌ NOT RESOLVED: Input '{input_val}' not recognized")
    
    # Test other menus
    print("\n📋 OTHER MENU TESTS:")
    other_menus = ["severity", "duration", "progression_status", "allergies", "on_medication", "consents"]
    
    for menu_name in other_menus:
        if menu_name in STRUCTURED_MENUS:
            menu = STRUCTURED_MENUS[menu_name]
            print(f"\n  Testing {menu_name} menu:")
            
            # Test first 3 options
            for i, (key, expected) in enumerate(list(menu["options"].items())[:3]):
                matched, result = MenuResolver.resolve(menu_name, key)
                status = "✅" if matched and result == expected else "❌" if not matched else "⚠️"
                print(f"    {key}: {result} {status}")
    
    print("\n" + "=" * 50)
    print("🎯 MENU RESOLUTION TESTS COMPLETE")
    print("=" * 50)

if __name__ == "__main__":
    test_menu_resolution()
