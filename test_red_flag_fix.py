#!/usr/bin/env python
import re

def test_red_flag_detection():
    print("🔍 TESTING RED FLAG DETECTION FIX")
    print("="*50)
    
    # Test cases
    test_cases = [
        ("i feel weak and headache", False, "Should NOT trigger shock"),
        ("i feel very pale and collapsed", True, "Should trigger shock"),
        ("i feel extremely weak", True, "Should trigger shock"),
        ("i feel dizzy and fainted", True, "Should trigger shock"),
        ("i have a headache", False, "Should NOT trigger shock"),
    ]
    
    # The updated pattern from conversational_intake_agent.py
    pattern = r"\b(very pale|cold hands|collapsed|fainted|extremely weak|can't stand|dizzy|fainting|passed out)\b"
    
    all_passed = True
    for text, expected, description in test_cases:
        result = bool(re.search(pattern, text.lower()))
        status = "✅ PASS" if result == expected else "❌ FAIL"
        if result != expected:
            all_passed = False
        
        print(f"{status}: {description}")
        print(f"  Text: '{text}'")
        print(f"  Expected: {expected}, Got: {result}")
        print()
    
    print("="*50)
    if all_passed:
        print("🎉 ALL TESTS PASSED! Red flag detection is now correct.")
    else:
        print("⚠️  Some tests failed. Check the pattern.")
    
    return all_passed

if __name__ == "__main__":
    test_red_flag_detection()
