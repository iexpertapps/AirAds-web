#!/usr/bin/env python3
"""
Debug script for GPS search issue
"""

import os
import sys
import django

# Setup Django
sys.path.append('/Users/syedsmacbook/Developer/AirAds-web/airaad/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from apps.vendors.models import Vendor, ClaimedStatus
from apps.vendors.claim_services import get_claimable_vendors

def test_gps_search():
    print("=== GPS Search Debug ===")
    
    # Test without coordinates
    print("\n1. Testing without coordinates:")
    try:
        result1 = get_claimable_vendors()
        print(f"   Found {len(result1)} vendors")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test with coordinates
    print("\n2. Testing with coordinates:")
    try:
        result2 = get_claimable_vendors(lat=31.373384470042097, lng=73.06685637991406)
        print(f"   Found {len(result2)} vendors")
    except Exception as e:
        print(f"   Error: {e}")
        import traceback
        traceback.print_exc()
    
    # Check vendor locations
    print("\n3. Checking vendor GPS data:")
    vendors = Vendor.objects.filter(is_deleted=False, claimed_status=ClaimedStatus.UNCLAIMED, qc_status__in=["APPROVED", "PENDING"])
    print(f"   Total vendors in filter: {vendors.count()}")
    
    for v in vendors[:3]:
        if v.gps_point:
            print(f"   - {v.business_name}: GPS({v.gps_point.x}, {v.gps_point.y})")
        else:
            print(f"   - {v.business_name}: No GPS data")

if __name__ == "__main__":
    test_gps_search()
