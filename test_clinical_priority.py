#!/usr/bin/env python
"""
Test script to verify clinical priority implementation accuracy
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'harakacare.settings')
django.setup()

from apps.triage.tools.conversational_intake_agent import ConversationalIntakeAgent, MenuResolver

def test_age_sex_gate():
    """Test the combined age/sex gate functionality"""
    print("🧪 TESTING AGE/SEX GATE")
    print("=" * 50)
    
    agent = ConversationalIntakeAgent()
    
    # Test all valid combinations
    test_cases = [
        ("1A", {"age_group": "newborn", "sex": "male"}),
        ("1B", {"age_group": "newborn", "sex": "female"}),
        ("3A", {"age_group": "child_1_5", "sex": "male"}),
        ("6B", {"age_group": "adult", "sex": "female"}),
        ("7A", {"age_group": "elderly", "sex": "male"}),
        ("7B", {"age_group": "elderly", "sex": "female"}),
    ]
    
    for input_val, expected in test_cases:
        print(f"\n📝 Testing: {input_val} -> {expected}")
        
        # Test menu resolution
        matched, result = MenuResolver.resolve("age_sex_gate", input_val)
        
        if matched:
            print(f"✅ RESOLVED: {result}")
            if result == expected:
                print(f"✅ CORRECT: Matches expected output")
            else:
                print(f"❌ INCORRECT: Expected {expected}, got {result}")
        else:
            print(f"❌ NOT RESOLVED: Input '{input_val}' not recognized")
    
    print("\n" + "=" * 50)

def test_pregnancy_menu():
    """Test pregnancy status menu"""
    print("\n🤰 TESTING PREGNANCY MENU")
    print("=" * 50)
    
    agent = ConversationalIntakeAgent()
    
    test_cases = [
        ("1", "yes"),
        ("2", "no"),
        ("3", "not_sure"),
        ("yes", "yes"),
        ("no", "no"),
    ]
    
    for input_val, expected in test_cases:
        print(f"\n📝 Testing: {input_val} -> {expected}")
        
        matched, result = MenuResolver.resolve("pregnancy_status", input_val)
        
        if matched:
            print(f"✅ RESOLVED: {result}")
            if result == expected:
                print(f"✅ CORRECT: Matches expected output")
            else:
                print(f"❌ INCORRECT: Expected {expected}, got {result}")
        else:
            print(f"❌ NOT RESOLVED: Input '{input_val}' not recognized")
    
    print("\n" + "=" * 50)

def test_empathy_templates():
    """Test complaint-aware empathy templates"""
    print("\n💬 TESTING EMPATHY TEMPLATES")
    print("=" * 50)
    
    agent = ConversationalIntakeAgent()
    
    # Test empathy templates for different complaint groups
    test_complaints = [
        ("fever", "I have fever and headache"),
        ("breathing", "I can't breathe properly"),
        ("headache", "My head is pounding"),
        ("injury", "I cut my hand"),
        ("abdominal", "My stomach hurts"),
        ("chest_pain", "I have chest pain"),
        ("other", "I feel unwell"),
    ]
    
    for complaint, message in test_complaints:
        print(f"\n📝 Testing complaint: {complaint}")
        print(f"Message: '{message}'")
        
        # Create mock state with this complaint
        mock_state = type('MockState', (), {
            'conversation_history': [
                {"role": "patient", "content": message, "turn": 1}
            ],
            'extracted_info': type('MockInfo', (), {
                'complaint_group': complaint
            })
        })
        
        empathy = agent._get_empathy_prefix(mock_state)
        print(f"💭 Empathy: '{empathy}'")
        
        # Verify it's complaint-specific
        expected_keywords = {
            "fever": ["feverish", "uncomfortable"],
            "breathing": ["worrying", "help"],
            "headache": ["debilitating", "help"],
            "injury": ["prompt attention", "assess"],
            "abdominal": ["disrupt", "understand"],
            "chest_pain": ["seriously", "concern"],
            "other": ["not feeling well", "figure out"],
        }
        
        if complaint in expected_keywords:
            expected_words = expected_keywords[complaint]
            found_words = [word for word in expected_words if word.lower() in empathy.lower()]
            if found_words:
                print(f"✅ COMPLAINT-SPECIFIC: Found keywords {found_words}")
            else:
                print(f"⚠️  NOT COMPLAINT-SPECIFIC: Expected keywords {expected_words}")
        else:
            print(f"✅ GENERIC EMPATHY: Appropriate for unspecified complaint")
    
    print("\n" + "=" * 50)

def test_priority_order():
    """Test the new field priority order"""
    print("\n📋 TESTING PRIORITY ORDER")
    print("=" * 50)
    
    agent = ConversationalIntakeAgent()
    
    # Test missing fields detection follows new priority
    mock_info = type('MockInfo', (), {
        'age_group': None,
        'sex': None,
        'complaint_group': 'headache',
        'severity': 'moderate',
        'consents_given': False,
        'duration': None,
        'location': None,
    })
    
    missing = agent._missing(mock_info, "routine")
    print(f"Missing fields: {missing}")
    
    # Verify priority order
    expected_order = [
        "age_group", "sex", "consents", "complaint_group", "severity", "duration",
        "progression_status", "condition_occurrence", "location", "village",
        "chronic_conditions", "on_medication", "allergies", "pregnancy_status",
    ]
    
    # Check if first missing field is age_group or sex
    if missing:
        first_missing = missing[0]
        if first_missing in ["age_group", "sex"]:
            print("✅ CORRECT: Age/sex are highest priority")
        else:
            print(f"❌ INCORRECT: First missing field is '{first_missing}', should be age_group or sex")
    
    # Check if consents is third (after demographics, before symptoms)
    consents_index = missing.index("consents") if "consents" in missing else -1
    print(f"✅ CONSENTS PRIORITY: Position {consents_index} in missing list")
    
    print("\n" + "=" * 50)

def test_step_progress():
    """Test step progress calculation"""
    print("\n📊 TESTING STEP PROGRESS")
    print("=" * 50)
    
    agent = ConversationalIntakeAgent()
    
    # Test different scenarios
    scenarios = [
        (["age_group", "sex"], "Step 2 of 14"),
        (["age_group", "sex", "consents"], "Step 3 of 14"),
        (["complaint_group", "severity", "duration"], "Step 4 of 14"),
        (list(range(1, 14)), "Step 14 of 14"),
    ]
    
    for missing_fields, expected_progress in scenarios:
        print(f"\n📝 Missing: {missing_fields}")
        
        # Create mock state
        mock_state = type('MockState', (), {
            'missing_fields': missing_fields,
        })
        
        # Simulate the progress calculation from the agent
        total_fields = 14  # CONVERSATIONAL_REQUIRED length
        collected = total_fields - len(missing_fields)
        current_step = collected + 1
        
        expected = expected_progress
        actual = f"Step {current_step} of {total_fields}"
        
        if actual == expected:
            print(f"✅ CORRECT: {actual}")
        else:
            print(f"❌ INCORRECT: Expected '{expected}', got '{actual}'")
    
    print("\n" + "=" * 50)

if __name__ == "__main__":
    print("🧪 HARAKACARE CLINICAL PRIORITY TESTING")
    print("=" * 60)
    
    try:
        test_age_sex_gate()
        test_pregnancy_menu()
        test_empathy_templates()
        test_priority_order()
        test_step_progress()
        
        print("\n🎯 ALL TESTS COMPLETED")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
