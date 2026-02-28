"""Quick E2E auth test for vendor portal."""
import json
import time
import urllib.request

BASE = "http://localhost:8001/api/v1"

def post(url, data):
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode(),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        try:
            return json.loads(body)
        except Exception:
            return {"success": False, "error": body[:300], "status": e.code}

def get(url, token):
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        try:
            body = json.loads(body)
        except Exception:
            body = body[:500]
        return e.code, body

# 1. Send OTP
print("=== 1. Send OTP ===")
time.sleep(2)
resp = post(f"{BASE}/vendor-portal/auth/send-otp/", {"phone": "+923001234567"})
print(f"  success={resp['success']}")

# 2. Verify OTP
print("=== 2. Verify OTP ===")
resp = post(f"{BASE}/vendor-portal/auth/verify-otp/", {"phone": "+923001234567", "otp": "005261"})
print(f"  success={resp['success']}")
if not resp.get("data") or not resp["data"].get("access"):
    print(f"  FAILED: {resp}")
    raise SystemExit(1)
token = resp["data"]["access"]
vendor_id = resp["data"]["user"]["vendor_id"]
print(f"  vendor_id={vendor_id}")
print(f"  token={token[:40]}...")

# 3. Dashboard
print("=== 3. Dashboard ===")
code, data = get(f"{BASE}/vendor-portal/dashboard/", token)
print(f"  status={code}, success={data.get('success') if isinstance(data, dict) else 'N/A'}")
if code != 200 and isinstance(data, str):
    import re
    # Extract the exception value from Django debug page
    match = re.search(r'<pre class="exception_value">(.*?)</pre>', data, re.DOTALL)
    if match:
        print(f"  exception: {match.group(1).strip()}")
    else:
        print(f"  error: {data[:500]}")

# 4. Me
print("=== 4. Me ===")
code, data = get(f"{BASE}/vendor-portal/auth/me/", token)
print(f"  status={code}, success={data.get('success') if isinstance(data, dict) else 'N/A'}")

# 5. Profile
print("=== 5. Profile ===")
code, data = get(f"{BASE}/vendor-portal/profile/", token)
print(f"  status={code}, success={data.get('success') if isinstance(data, dict) else 'N/A'}")

# 6. Discounts
print("=== 6. Discounts ===")
code, data = get(f"{BASE}/vendor-portal/discounts/", token)
print(f"  status={code}, success={data.get('success') if isinstance(data, dict) else 'N/A'}")

# 7. Reels
print("=== 7. Reels ===")
code, data = get(f"{BASE}/vendor-portal/reels/", token)
print(f"  status={code}, success={data.get('success') if isinstance(data, dict) else 'N/A'}")

# 8. Voicebot
print("=== 8. Voicebot ===")
code, data = get(f"{BASE}/vendor-portal/voice-bot/", token)
print(f"  status={code}, success={data.get('success') if isinstance(data, dict) else 'N/A'}")

# 9. Analytics summary
print("=== 9. Analytics Summary ===")
code, data = get(f"{BASE}/analytics/vendors/{vendor_id}/summary/", token)
print(f"  status={code}, success={data.get('success') if isinstance(data, dict) else 'N/A'}")

# 10. Completeness
print("=== 10. Completeness ===")
code, data = get(f"{BASE}/vendor-portal/profile/completeness/", token)
print(f"  status={code}, success={data.get('success') if isinstance(data, dict) else 'N/A'}")

# 11. Subscription status
print("=== 11. Subscription Status ===")
code, data = get(f"{BASE}/payments/subscription-status/", token)
print(f"  status={code}, success={data.get('success') if isinstance(data, dict) else 'N/A'}")

# 12. Invoices
print("=== 12. Invoices ===")
code, data = get(f"{BASE}/payments/invoices/", token)
print(f"  status={code}, success={data.get('success') if isinstance(data, dict) else 'N/A'}")

print("\n=== DONE ===")
