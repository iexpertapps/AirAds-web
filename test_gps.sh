#!/bin/bash

echo "Testing GPS search API..."
curl -s "http://localhost:8000/api/v1/vendor-portal/claim/search/?lat=31.373384470042097&lng=73.06685637991406" | head -5
