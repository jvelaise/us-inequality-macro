#!/usr/bin/env bash
# Rebuild everything from data/raw/ -> docs/index.html, then run the checks.
# Usage:  bash run_all.sh            (stops at the first failing step)
set -euo pipefail
cd "$(dirname "$0")"
step() { echo; echo "== $1"; }
step "1/5 build annual panel";        python code/01_build_panel.py
step "2/5 estimate + chart";          python code/02_estimate_and_plot.py
step "3/5 PDF summary";               python code/03_build_report.py
step "4/5 website";                   python code/04_build_site.py
step "5/5 tests";                     python -m pytest -q
echo; echo "Done. Open docs/index.html in a browser to preview."
