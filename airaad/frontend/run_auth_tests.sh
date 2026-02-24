#!/bin/sh
cd /Users/syedsmacbook/Developer/AirAds-web/airaad/frontend
npx playwright test e2e/auth.spec.ts --project=chromium --reporter=line
