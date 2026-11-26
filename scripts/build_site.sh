#!/usr/bin/env bash
# Build the public static site (invest.bolujo.com).
# Cloudflare Workers Builds runs this from the repository root (see wrangler.jsonc):
#   Build command:           bash scripts/build_site.sh
#   Deploy command:          npx wrangler deploy  (uploads site/)
# It downloads the pinned dataset, scans every stock with the default settings and writes site/data/.
set -euo pipefail
python --version
python -m pip install --quiet --upgrade pip
python -m pip install --quiet .
python -m scanner.publish --out site/data
echo "Site ready in site/ ($(ls site/data/stocks | wc -l | tr -d ' ') stocks)"
