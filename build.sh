#!/bin/bash
# Build frontend and package addon
set -e

echo "=== Building HA Agent Add-on ==="

# Build React frontend
cd frontend
npm install
npm run build
cd ..

echo "=== Frontend built ==="
echo "=== Ready to deploy ==="
echo ""
echo "Next steps:"
echo "1. Copy this folder to your HA config: /addons/ha_agent/"
echo "2. In HA: Settings → Add-ons → Add-on Store → ⋮ → Check for updates"
echo "3. Find 'HA Agent' in local add-ons → Install"
echo "4. In Configuration tab: add your Anthropic API Key"
echo "5. Start the add-on"
