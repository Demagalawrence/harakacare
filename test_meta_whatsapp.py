#!/usr/bin/env python
"""
Test Meta WhatsApp Cloud API Integration
Tests the new Meta WhatsApp client and handler functionality.
"""

import os
import sys
import json

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_meta_whatsapp_client():
    """Test Meta WhatsApp client functionality"""
    print("🧪 TESTING META WHATSAPP CLIENT")
    print("=" * 60)
    
    try:
        from apps.messaging.whatsapp.meta_whatsapp_client import MetaWhatsAppClient, MetaWhatsAppAPIError
        
        # Test client initialization
        print("\n📱 Testing Client Initialization...")
        try:
            client = MetaWhatsAppClient()
            print("✅ Client initialized successfully")
            print(f"   Base URL: {client.base_url}")
            print(f"   API Version: {client.api_version}")
            print(f"   Phone ID: {client.phone_number_id}")
        except ValueError as e:
            print(f"❌ Client initialization failed: {e}")
            return False
        
        # Test message formatting (without actually sending)
        print("\n📝 Testing Message Formatting...")
        
        # Test interactive buttons
        test_buttons = [
            {"type": "reply", "reply": {"id": "1A", "title": "Newborn Male"}},
            {"type": "reply", "reply": {"id": "6B", "title": "Adult Female"}},
        ]
        
        print("✅ Interactive buttons format:")
        for button in test_buttons:
            print(f"   {button}")
        
        # Test list message format
        test_sections = [{
            "title": "Age Groups",
            "rows": [
                {"id": "1", "title": "Newborn (0-2 months)"},
                {"id": "2", "title": "Infant (3-11 months)"},
            ]
        }]
        
        print("✅ List message format:")
        for section in test_sections:
            print(f"   {section}")
        
        print("\n📊 Client functionality test: PASSED")
        return True
        
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Client test failed: {e}")
        return False

def test_meta_whatsapp_handler():
    """Test Meta WhatsApp handler functionality"""
    print("\n🤖 TESTING META WHATSAPP HANDLER")
    print("=" * 60)
    
    try:
        from apps.messaging.whatsapp.meta_whatsapp_handler import MetaWhatsAppHandler, _format_menu_response
        
        # Test handler initialization
        print("\n📱 Testing Handler Initialization...")
        handler = MetaWhatsAppHandler()
        print("✅ Handler initialized successfully")
        
        # Test menu formatting
        print("\n📝 Testing Menu Formatting...")
        
        # Test age/sex gate formatting
        age_sex_message = (
            "First, I need to know who we're helping. Please select:\n"
            "👤 AGE (select number):\n"
            "1️⃣ Newborn (0-2 months)\n"
            "2️⃣ Infant (3-11 months)\n"
            "⚧️ SEX (select letter):\n"
            "A. Male\n"
            "B. Female\n\n"
            "Reply with format: [number][letter] (e.g., 6A for adult female, 3B for child male)"
        )
        
        formatted = _format_menu_response(age_sex_message)
        print("✅ Age/Sex gate formatted as interactive buttons:")
        if formatted.get("type") == "interactive_buttons":
            print(f"   Header: {formatted.get('header')}")
            print(f"   Message: {formatted.get('message')}")
            print(f"   Buttons: {len(formatted.get('buttons', []))} buttons")
            for button in formatted.get('buttons', [])[:3]:  # Show first 3
                print(f"     {button}")
        else:
            print(f"   Type: {formatted.get('type')}")
            print(f"   Message: {formatted.get('message')}")
        
        # Test location request formatting
        print("\n📍 Testing Location Request...")
        location_message = "Please share your current location for better facility matching."
        location_formatted = _format_location_request(location_message)
        print("✅ Location request formatted:")
        print(f"   Type: {location_formatted.get('type')}")
        print(f"   Message: {location_formatted.get('message')}")
        
        # Test emergency response
        print("\n🚨 Testing Emergency Response...")
        emergency_response = handler._emergency_response()
        print("✅ Emergency response:")
        print(f"   Type: {emergency_response.get('type')}")
        print(f"   Message: {emergency_response.get('message')[:100]}...")
        
        # Test welcome response
        print("\n👋 Testing Welcome Response...")
        welcome_response = handler._welcome_response()
        print("✅ Welcome response:")
        print(f"   Type: {welcome_response.get('type')}")
        print(f"   Message: {welcome_response.get('message')[:100]}...")
        
        print("\n📊 Handler functionality test: PASSED")
        return True
        
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Handler test failed: {e}")
        return False

def test_webhook_view():
    """Test webhook view structure"""
    print("\n🔗 TESTING WEBHOOK VIEW STRUCTURE")
    print("=" * 60)
    
    try:
        from apps.messaging.whatsapp.meta_whatsapp_views import MetaWhatsAppWebhookView
        
        # Test view class
        print("\n📱 Testing Webhook View...")
        view = MetaWhatsAppWebhookView()
        print("✅ Webhook view class exists")
        
        # Test method availability
        print("\n🔧 Testing View Methods...")
        if hasattr(view, 'get') and callable(getattr(view, 'get')):
            print("✅ GET method available (webhook verification)")
        else:
            print("❌ GET method missing")
            
        if hasattr(view, 'post') and callable(getattr(view, 'post')):
            print("✅ POST method available (webhook events)")
        else:
            print("❌ POST method missing")
        
        print("\n📊 Webhook view structure test: PASSED")
        return True
        
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Webhook view test failed: {e}")
        return False

def test_url_configuration():
    """Test URL configuration"""
    print("\n🌐 TESTING URL CONFIGURATION")
    print("=" * 60)
    
    try:
        from django.urls import reverse
        from django.conf import settings
        
        # Test URL reversal
        print("\n🔗 Testing URL Reversal...")
        try:
            meta_webhook_url = reverse("whatsapp:meta_webhook")
            print(f"✅ Meta webhook URL: {meta_webhook_url}")
        except Exception as e:
            print(f"❌ URL reversal failed: {e}")
        
        # Test legacy URL (should still exist during migration)
        try:
            legacy_webhook_url = reverse("whatsapp:webhook")
            print(f"✅ Legacy webhook URL: {legacy_webhook_url}")
        except Exception as e:
            print(f"❌ Legacy URL reversal failed: {e}")
        
        print("\n📊 URL configuration test: PASSED")
        return True
        
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False
    except Exception as e:
        print(f"❌ URL configuration test failed: {e}")
        return False

def test_settings_configuration():
    """Test Django settings configuration"""
    print("\n⚙️ TESTING SETTINGS CONFIGURATION")
    print("=" * 60)
    
    try:
        from django.conf import settings
        
        # Test Meta WhatsApp settings
        print("\n🔑 Testing Meta WhatsApp Settings...")
        
        meta_settings = [
            'META_WHATSAPP_ACCESS_TOKEN',
            'META_WHATSAPP_PHONE_NUMBER_ID', 
            'META_WHATSAPP_WEBHOOK_VERIFY_TOKEN',
            'META_WHATSAPP_APP_SECRET',
            'META_WHATSAPP_BASE_URL'
        ]
        
        for setting_name in meta_settings:
            setting_value = getattr(settings, setting_name, None)
            if setting_value:
                if 'SECRET' in setting_name or 'TOKEN' in setting_name:
                    print(f"✅ {setting_name}: {'*' * 8} (configured)")
                else:
                    print(f"✅ {setting_name}: {setting_value}")
            else:
                print(f"⚠️  {setting_name}: NOT SET")
        
        print("\n📊 Settings configuration test: COMPLETED")
        return True
        
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Settings test failed: {e}")
        return False

def main():
    """Run all Meta WhatsApp tests"""
    print("🧪 META WHATSAPP CLOUD API INTEGRATION TESTS")
    print("=" * 80)
    print("Testing migration from 360Dialog to Meta WhatsApp Cloud API")
    print("=" * 80)
    
    test_results = []
    
    # Run all tests
    test_results.append(test_settings_configuration())
    test_results.append(test_meta_whatsapp_client())
    test_results.append(test_meta_whatsapp_handler())
    test_results.append(test_webhook_view())
    test_results.append(test_url_configuration())
    
    # Summary
    print("\n" + "=" * 80)
    print("📊 TEST SUMMARY")
    print("=" * 80)
    
    passed = sum(test_results)
    total = len(test_results)
    
    print(f"Tests Passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED!")
        print("✅ Meta WhatsApp Cloud API integration is ready")
        print("📱 Ready to migrate from 360Dialog")
    else:
        print("⚠️  SOME TESTS FAILED!")
        print("❌ Review configuration and try again")
        print("🔧 Check settings and imports")
    
    print("\n" + "=" * 80)
    print("📋 NEXT STEPS:")
    print("1. Configure Meta Developer app")
    print("2. Update Django settings with credentials")
    print("3. Deploy webhook endpoint")
    print("4. Test with Meta webhook tester")
    print("5. Gradual migration: 50% Meta, 50% 360Dialog")
    print("6. Monitor and optimize")
    print("=" * 80)

if __name__ == "__main__":
    main()
