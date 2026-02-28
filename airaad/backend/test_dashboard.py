"""Hit dashboard and print full error."""
import json, urllib.request, urllib.error, re

BASE = "http://localhost:8001/api/v1"

# Get token
req = urllib.request.Request(
    f"{BASE}/vendor-portal/auth/verify-otp/",
    data=json.dumps({"phone": "+923001234567", "otp": "005261"}).encode(),
    headers={"Content-Type": "application/json"},
)
with urllib.request.urlopen(req) as r:
    token = json.loads(r.read())["data"]["access"]

# Hit dashboard
req = urllib.request.Request(
    f"{BASE}/vendor-portal/dashboard/",
    headers={"Authorization": f"Bearer {token}"},
)
try:
    with urllib.request.urlopen(req) as r:
        print("OK:", r.status)
except urllib.error.HTTPError as e:
    body = e.read().decode()
    # Extract exception value
    m = re.search(r'Exception Value:.*?<pre.*?>(.*?)</pre>', body, re.DOTALL)
    if m:
        print("Exception:", m.group(1).strip())
    # Extract traceback
    m2 = re.search(r'<textarea[^>]*id="traceback_area"[^>]*>(.*?)</textarea>', body, re.DOTALL)
    if m2:
        print("\nTraceback:")
        print(m2.group(1).strip()[:2000])
    if not m and not m2:
        # Try finding any pre tag with useful info
        for match in re.finditer(r'<pre[^>]*>(.*?)</pre>', body, re.DOTALL):
            txt = match.group(1).strip()
            if len(txt) > 20:
                print(txt[:1500])
                break
