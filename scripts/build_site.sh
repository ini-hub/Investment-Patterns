#!/usr/bin/env bash
# Build the public static site (investment.bolujo.com).
# Cloudflare Pages runs this from the repository root:
#   Build command:           bash scripts/build_site.sh
#   Build output directory:  site
# It downloads the pinned dataset, scans every stock with the default settings and writes site/data/.
set -euo pipefail
python --version
python -m pip install --quiet --upgrade pip
python -m pip install --quiet .
python -m scanner.publish --out site/data
echo "Site ready in site/ ($(ls site/data/stocks | wc -l | tr -d ' ') stocks)"
