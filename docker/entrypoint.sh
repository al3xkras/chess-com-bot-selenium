#!/bin/bash
cd "$(dirname "$0")" || exit 1

while ((1)); do
    venv/bin/python src/main.py
done
