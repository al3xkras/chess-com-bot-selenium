#!/bin/bash

set -e
cd "$(dirname "$0")" || exit 1

VENV=$(realpath ./venv)
STOCKFISH_PATH=$(realpath ./stockfish/stockfish)

if [ ! -d "$VENV" ]; then
    which virtualenv
    if [ ! $? ]; then
        echo "Installing virtualenv..."
        pip install virtualenv
    fi
    virtualenv venv
    venv/bin/pip install -r ./requirements.txt
fi

if [ ! -f "$STOCKFISH_PATH" ]; then
    mkdir -p "$(dirname "$STOCKFISH_PATH")"
    which wget || exit 1
    which tar || exit 1
    echo "Downloading and extracting Stockfish to ./stockfish"
    wget https://github.com/official-stockfish/Stockfish/releases/download/sf_16/stockfish-ubuntu-x86-64.tar
    tar -xvf stockfish-ubuntu-x86-64.tar && mv stockfish/stockfish-ubuntu-x86-64 stockfish/stockfish
    rm "./stockfish-ubuntu-x86-64.tar"
fi

"$VENV/bin/python" main.py --elo-rating -1 --game-timer-ms 150000 --first-move-w e2e4 --next-game-auto True
