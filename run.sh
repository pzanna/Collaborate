#!/bin/bash

# Run script for the Collaborate project
# This ensures the correct Python environment is used

cd "$(dirname "$0")"
.venv/bin/python src/main.py
