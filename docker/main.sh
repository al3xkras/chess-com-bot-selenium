#!/bin/bash
cd "$(dirname "$0")" || exit 1
venv/bin/python main.py --elo-rating -1 --game-timer-ms 150000 --first-move-w e2e4