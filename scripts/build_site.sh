#!/usr/bin/env bash
# Build the public static site (invest.bolujo.com).
# On Cloudflare, `npx wrangler deploy` runs this from the repository root before uploading site/
# (the `build` block in wrangler.jsonc).
# It downloads the pinned dataset, scans every stock with the default settings and writes site/data/.
set -euo pipefail
python --version
python -m pip install --quiet --upgrade pip
python -m pip install --quiet .
python -m scanner.publish --out site/data
echo "Site ready in site/ ($(ls site/data/stocks | wc -l | tr -d ' ') stocks)"
