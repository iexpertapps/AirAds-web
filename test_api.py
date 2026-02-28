import requests
import json

# Test the API endpoint
url = "http://localhost:8000/api/v1/vendor-portal/claim/search/?lat=31.373384470042097&lng=73.06685637991406"

try:
    response = requests.get(url)
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"Success: {data.get('success')}")
        print(f"Message: {data.get('message')}")
        print(f"Vendors found: {len(data.get('data', []))}")
    else:
        print(f"Error: {response.text[:500]}")
        
except Exception as e:
    print(f"Request failed: {e}")
