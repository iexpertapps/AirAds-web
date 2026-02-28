#!/usr/bin/env python

# Test GPS coordinates directly
import os
import sys
import django

sys.path.append('/Users/syedsmacbook/Developer/AirAds-web/airaad/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from apps.vendors.models import Vendor, ClaimedStatus

print("=== Vendor GPS Data Check ===")
vendors = Vendor.objects.filter(is_deleted=False, claimed_status=ClaimedStatus.UNCLAIMED, qc_status__in=["APPROVED", "PENDING"])

print(f"Total vendors: {vendors.count()}")

# Check coordinates
for v in vendors:
    if v.gps_point:
        print(f"{v.business_name}: GPS({v.gps_point.x:.6f}, {v.gps_point.y:.6f})")
        
        # Test if our search coordinates would include this vendor
        search_lat, search_lng = 31.373384470042097, 73.06685637991406
        lat_delta, lng_delta = 1.0, 1.0
        
        min_lat, max_lat = search_lat - lat_delta, search_lat + lat_delta
        min_lng, max_lng = search_lng - lng_delta, search_lng + lng_delta
        
        in_range = (min_lng <= v.gps_point.x <= max_lng and 
                   min_lat <= v.gps_point.y <= max_lat)
        
        print(f"  -> In search range: {in_range}")
        if in_range:
            print(f"  -> Should be found!")
    else:
        print(f"{v.business_name}: No GPS data")
