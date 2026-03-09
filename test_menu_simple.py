#!/usr/bin/env python
"""
Standalone test for menu resolution - no Django dependencies
"""

# Test the menu structures directly
STRUCTURED_MENUS = {
    "age_sex_gate": {
        "prompt": (
            "First, I need to know who we're helping. Please select:\n"
            "👤 AGE (select number):\n"
            "1️⃣ Newborn (0-2 months)\n"
            "2️⃣ Infant (3-11 months)\n"
            "3️⃣ Child (1-5 years)\n"
            "4️⃣ Child (6-12 years)\n"
            "5️⃣ Teen (13-17 years)\n"
            "6️⃣ Adult (18-64 years)\n"
            "7️⃣ Elderly (65+ years)\n\n"
            "⚧️ SEX (select letter):\n"
            "A. Male\n"
            "B. Female\n\n"
            "Reply with format: [number][letter] (e.g., 6A for adult female, 3B for child male)"
        ),
        "options": {
            "1A": {"age_group": "newborn", "sex": "male"},
            "1B": {"age_group": "newborn", "sex": "female"},
            "2A": {"age_group": "infant", "sex": "male"},
            "2B": {"age_group": "infant", "sex": "female"},
            "3A": {"age_group": "child_1_5", "sex": "male"},
            "3B": {"age_group": "child_1_5", "sex": "female"},
            "4A": {"age_group": "child_6_12", "sex": "male"},
            "4B": {"age_group": "child_6_12", "sex": "female"},
            "5A": {"age_group": "teen", "sex": "male"},
            "5B": {"age_group": "teen", "sex": "female"},
            "6A": {"age_group": "adult", "sex": "male"},
            "6B": {"age_group": "adult", "sex": "female"},
            "7A": {"age_group": "elderly", "sex": "male"},
            "7B": {"age_group": "elderly", "sex": "female"},
        },
    },
    "pregnancy_status": {
        "prompt": (
            "🤰 Is the patient currently pregnant?\n"
            "1️⃣ Yes\n"
            "2️⃣ No\n"
            "3️⃣ Not sure\n"
            "Reply with 1, 2, or 3."
        ),
        "options": {
            "1": "yes",      "yes": "yes",      "pregnant": "yes",
            "2": "no",       "no": "no",        "not pregnant": "no",
            "3": "not_sure", "not sure": "not_sure", "unsure": "not_sure", "maybe": "not_sure",
        },
    },
}

def resolve_menu(field_name, user_input):
    """Simple menu resolution function"""
    menu = STRUCTURED_MENUS.get(field_name)
    if not menu:
        return False, None
    
    user_input = user_input.strip().lower()
    options = menu["options"]
    
    # Exact match first
    if user_input in options:
        return True, options[user_input]
    
    # Check if response is just a number matching a menu option
    import re
    if re.match(r"^\d+$", user_input) and user_input in options:
        return True, options[user_input]
    
    # Partial match for longer responses
    for key, value in options.items():
        if len(key) > 1 and key in user_input:
            return True, value
    
    # Special handling for combined age/sex gate (e.g., "1A", "6B")
    if field_name == "age_sex_gate":
        # Check for combined patterns like "1A", "6B", "3a", "7B"
        combined_match = re.match(r"^(\d)([ab])$", user_input)
        if combined_match:
            number = combined_match.group(1)
            letter = combined_match.group(2).upper()
            combined_key = f"{number}{letter}"
            if combined_key in options:
                return True, options[combined_key]
    
    return False, None

def test_menu_resolution():
    """Test the menu resolution accuracy"""
    print("🧪 TESTING MENU RESOLUTION ACCURACY")
    print("=" * 60)
    
    all_passed = True
    
    # Test age_sex_gate
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
        ("6b", {"age_group": "adult", "sex": "female"}),  # Test case insensitive
        (" 6b ", {"age_group": "adult", "sex": "female"}),  # Test with spaces
    ]
    
    for input_val, expected in test_cases:
        matched, result = resolve_menu("age_sex_gate", input_val)
        
        if matched and result == expected:
            print(f"  ✅ PASS: '{input_val}' -> {result}")
        elif matched:
            print(f"  ❌ FAIL: '{input_val}' -> {result} (expected {expected})")
        else:
            print(f"  ⚠️  NOT RECOGNIZED: '{input_val}'")
            all_passed = False
    
    # Test pregnancy_status
    print("\n🤰 PREGNANCY STATUS TESTS:")
    pregnancy_tests = [
        ("1", "yes"),
        ("2", "no"), 
        ("3", "not_sure"),
        ("YES", "yes"),  # Test case insensitive
        ("no", "no"),
        ("invalid", None),
    ]
    
    for input_val, expected in pregnancy_tests:
        matched, result = resolve_menu("pregnancy_status", input_val)
        
        if matched and result == expected:
            print(f"  ✅ PASS: '{input_val}' -> {result}")
        elif matched:
            print(f"  ❌ FAIL: '{input_val}' -> {result} (expected {expected})")
        else:
            print(f"  ⚠️  NOT RECOGNIZED: '{input_val}'")
            all_passed = False
    
    # Test other menus
    print("\n📋 OTHER MENU TESTS:")
    other_menus = ["severity", "duration", "progression_status", "allergies", "on_medication", "consents"]
    
    for menu_name in other_menus:
        if menu_name in STRUCTURED_MENUS:
            menu = STRUCTURED_MENUS[menu_name]
            print(f"\n  Testing {menu_name} menu:")
            
            # Test first 3 options
            for i, (key, expected) in enumerate(list(menu["options"].items())[:3]):
                matched, result = resolve_menu(menu_name, key)
                status = "✅" if matched and result == expected else "❌" if not matched else "⚠️"
                print(f"    {key}: {result} {status}")
    
    print("\n" + "=" * 60)
    
    if all_passed:
        print("🎉 ALL TESTS PASSED!")
        print("✅ Menu resolution working correctly")
    else:
        print("⚠️  SOME TESTS FAILED!")
        print("❌ Menu resolution needs fixes")
    
    print("\n" + "=" * 60)
    print("🎯 MENU RESOLUTION TEST COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    test_menu_resolution()
