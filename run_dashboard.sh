#!/bin/bash
cd "$(dirname "$0")"
source .venv/bin/activate
python dashboard.py --path "$1"
