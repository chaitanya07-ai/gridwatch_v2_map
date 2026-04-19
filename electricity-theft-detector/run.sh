#!/bin/bash
echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║         GridWatch — Electricity Theft Detection              ║"
echo "╠══════════════════════════════════════════════════════════════╣"
echo "║  Smart Meters  →  http://localhost:5000/meters               ║"
echo "║  Transformers  →  http://localhost:5000/transformers         ║"
echo "║  Live Map      →  http://localhost:5000/map                  ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# Check Python
if ! command -v python3 &>/dev/null; then
  echo "ERROR: python3 not found"
  exit 1
fi

# Install deps if needed
pip install flask --quiet --break-system-packages 2>/dev/null || \
pip install flask --quiet 2>/dev/null

# Run
python3 app.py
