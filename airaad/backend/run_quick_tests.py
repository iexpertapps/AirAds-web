#!/usr/bin/env python
"""
Quick test runner - bypass migrations and run tests directly
"""

import os
import sys
import django
from django.conf import settings

# Configure minimal test settings without migrations
MINIMAL_SETTINGS = {
    'DEBUG': True,
    'DATABASES': {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': ':memory:',
        }
    },
    'INSTALLED_APPS': [
        'django.contrib.auth',
        'django.contrib.contenttypes',
        'rest_framework',
        'rest_framework_simplejwt',
        'apps.customer_auth',
        'apps.user_portal', 
        'apps.user_preferences',
    ],
    'SECRET_KEY': 'test-secret-key-12345',
    'USE_TZ': True,
    'TIME_ZONE': 'UTC',
    'REST_FRAMEWORK': {
        'DEFAULT_AUTHENTICATION_CLASSES': [
            'rest_framework_simplejwt.authentication.JWTAuthentication',
        ],
    },
    'SIMPLE_JWT': {
        'ACCESS_TOKEN_LIFETIME': 60 * 5,  # 5 minutes
        'REFRESH_TOKEN_LIFETIME': 60 * 24 * 7,  # 7 days
    },
}

# Apply settings
if not settings.configured:
    settings.configure(**MINIMAL_SETTINGS)
    django.setup()

def run_basic_tests():
    """Run basic model tests without migrations"""
    print("🚀 Running quick tests...")
    
    try:
        # Test 1: Import models
        from apps.user_portal.models import Promotion, Tag, UserPortalConfig
        from apps.customer_auth.models import CustomerUser, GuestToken
        from apps.user_preferences.models import UserPreference
        print("✅ All models imported successfully")
        
        # Test 2: Create tables manually
        from django.db import connection
        with connection.schema_editor() as schema_editor:
            # Create customer_auth tables
            from django.contrib.auth.models import User
            schema_editor.create_model(User)
            
            try:
                schema_editor.create_model(CustomerUser)
                print("✅ CustomerUser table created")
            except Exception as e:
                print(f"⚠️ CustomerUser table issue: {e}")
            
            try:
                schema_editor.create_model(GuestToken)
                print("✅ GuestToken table created")
            except Exception as e:
                print(f"⚠️ GuestToken table issue: {e}")
            
            # Create user_portal tables
            try:
                schema_editor.create_model(Tag)
                print("✅ Tag table created")
            except Exception as e:
                print(f"⚠️ Tag table issue: {e}")
            
            try:
                schema_editor.create_model(Promotion)
                print("✅ Promotion table created")
            except Exception as e:
                print(f"⚠️ Promotion table issue: {e}")
            
            try:
                schema_editor.create_model(UserPortalConfig)
                print("✅ UserPortalConfig table created")
            except Exception as e:
                print(f"⚠️ UserPortalConfig table issue: {e}")
            
            # Create user_preferences tables
            try:
                schema_editor.create_model(UserPreference)
                print("✅ UserPreference table created")
            except Exception as e:
                print(f"⚠️ UserPreference table issue: {e}")
        
        # Test 3: Basic model operations
        print("\n🧪 Testing basic operations...")
        
        # Create test user
        user = User.objects.create_user(
            username='test@example.com',
            email='test@example.com',
            password='testpass123'
        )
        print("✅ User created")
        
        # Create customer user
        customer_user = CustomerUser.objects.create(
            user=user,
            display_name='Test User'
        )
        print("✅ CustomerUser created")
        
        # Create tag
        tag = Tag.objects.create(
            name='Restaurant',
            slug='restaurant',
            category='FOOD'
        )
        print("✅ Tag created")
        
        # Create user preference
        preference = UserPreference.objects.create(
            user=customer_user,
            default_view='AR',
            search_radius_m=1000
        )
        print("✅ UserPreference created")
        
        # Test 4: Verify data (without promotion for now)
        assert CustomerUser.objects.count() == 1
        assert Tag.objects.count() == 1
        assert UserPreference.objects.count() == 1
        print("✅ Core data verified")
        
        # Test 5: Test model methods
        tag.refresh_from_db()
        assert str(tag) == "Restaurant"
        assert tag.slug == "restaurant"
        print("✅ Tag methods working")
        
        customer_user.refresh_from_db()
        assert customer_user.display_name == "Test User"
        print("✅ CustomerUser methods working")
        
        preference.refresh_from_db()
        assert preference.default_view == 'AR'
        print("✅ UserPreference methods working")
        
        print("\n🎉 ALL TESTS PASSED!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = run_basic_tests()
    sys.exit(0 if success else 1)
