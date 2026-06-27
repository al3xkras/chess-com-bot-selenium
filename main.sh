#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(dirname "$0")"
SCRIPT_DIR="$(realpath $SCRIPT_DIR)"
cd $SCRIPT_DIR || exit 1

ENV_FILE_NAME=config.env
COMPOSE_FILE="$(realpath ./docker/docker-compose.yml)"

# --------------------------------------------------
# Load .env file if present (docker-compose style)
# --------------------------------------------------
if [ -f "$SCRIPT_DIR/$ENV_FILE_NAME" ]; then
    echo "Loading configuration from $SCRIPT_DIR/$ENV_FILE_NAME"
    set -o allexport
    # shellcheck disable=SC1090
    source "$SCRIPT_DIR/$ENV_FILE_NAME"
    set +o allexport
fi

docker(){
    sudo -E docker $@
}

is_true() {
    case "${1,,}" in
        1|true)  return 0 ;;
        0|false) return 1 ;;
        *)
            echo "Invalid boolean value: $1" >&2
            return 2
            ;;
    esac
}

start_local(){
    # --------------------------------------------------
    # Defaults (can be overridden by .env or env vars)
    # --------------------------------------------------
    : "${ELO_RATING:=-1}"
    : "${GAME_TIMER_MS:=150000}"
    : "${FIRST_MOVE_W:=e2e4}"
    : "${NEXT_GAME_AUTO:=True}"
    : "${STOCKFISH_VERSION:=sf_16}"
    : "${STOCKFISH_ARCHIVE:=stockfish-ubuntu-x86-64.tar}"
    : "${STOCKFISH_URL:=https://github.com/official-stockfish/Stockfish/releases/download/${STOCKFISH_VERSION}/${STOCKFISH_ARCHIVE}}"

    VENV="$SCRIPT_DIR/venv"
    STOCKFISH_DIR="$SCRIPT_DIR/stockfish"
    STOCKFISH_PATH="$STOCKFISH_DIR/stockfish"

    # --------------------------------------------------
    # Virtualenv setup
    # --------------------------------------------------
    if [ ! -d "$VENV" ]; then
        echo "Creating virtualenv..."
        if ! command -v virtualenv >/dev/null 2>&1; then
            echo "Installing virtualenv..."
            pip install virtualenv
        fi

        virtualenv "$VENV"
        "$VENV/bin/pip" install -r "$SCRIPT_DIR/requirements.txt"
    fi

    [ ! -d $STOCKFISH_DIR ] && mkdir -p $STOCKFISH_DIR

    # --------------------------------------------------
    # Stockfish setup
    # --------------------------------------------------
    if [ ! -f "$STOCKFISH_PATH" ]; then
        echo "Downloading and extracting Stockfish..."

        mkdir -p "$STOCKFISH_DIR"

        command -v wget >/dev/null 2>&1 || { echo "wget not found"; exit 1; }
        command -v tar >/dev/null 2>&1 || { echo "tar not found"; exit 1; }

        wget -O "$STOCKFISH_ARCHIVE" "$STOCKFISH_URL"
        tar -xvf "$STOCKFISH_ARCHIVE"

        mv stockfish/stockfish-ubuntu-x86-64 "$STOCKFISH_PATH"
        chmod +x "$STOCKFISH_PATH"

        rm "$STOCKFISH_ARCHIVE"
    fi

    #exec "$VENV/bin/python" src/main.py --help

    # -------------------------------------------------
    # Run application
    # --------------------------------------------------
    exec "$VENV/bin/python" src/main.py \
        --elo-rating "$ELO_RATING" \
        --game-timer-ms "$GAME_TIMER_MS" \
        --first-move-w "$FIRST_MOVE_W" \
        --enable-move-delay "$ENABLE_MOVE_DELAY" \
        --next-game-auto "$START_NEW_GAME_AUTOMATICALLY" \
        --autostart "$AUTOSTART_FIRST_GAME" \
        --game-type="$GAME_TYPE"
}

start_docker(){
    if $(is_true $OPEN_BROWSER) && [[ "$compose_args" = *"up"* ]]; then
        echo "Opening container URLs automatically"
        open_ports_in_webbrowser &
    fi
    echo "Compose args: $compose_args; Compose file: $COMPOSE_FILE"
    docker compose -f $COMPOSE_FILE $compose_args
}

wait_for_port() {
    local port="$1"
    echo "Waiting for localhost:${port}..."
    # Wait until TCP connection succeeds
    until nc -z localhost "$port" 2>/dev/null; do
        sleep 0.5
    done
    echo "Port ${port} is reachable."
}

open_port() {
    local port="$1"
    wait_for_port "$port"
    python3 -m webbrowser "http://localhost:${port}?autoconnect=1&resize=scale"
}

open_ports_in_webbrowser(){
    if [[ -z "${REPLICA_PORTS:-}" ]]; then
        echo "Error: REPLICA_PORTS is not set"
        exit 1
    fi

    # Range case
    if [[ "$REPLICA_PORTS" =~ ^([0-9]+)-([0-9]+)$ ]]; then

        start="${BASH_REMATCH[1]}"
        end="${BASH_REMATCH[2]}"

        if (( start > end )); then
            echo "Error: Invalid range ($start > $end)"
            exit 1
        fi

        for ((port=start; port<=end; port++)); do
            open_port "$port"
        done

    # Single port case
    elif [[ "$REPLICA_PORTS" =~ ^[0-9]+$ ]]; then
        open_port "$REPLICA_PORTS"
    else
        echo "Error: REPLICA_PORTS must be a single port (e.g. 7910) or range (e.g. 7910-7913)"
        exit 1
    fi
}

compose_args="${@:1}"
if [ -z "$compose_args" ]; then
    compose_args="up --build"    
fi

if [ "$STARTUP_TYPE" = "docker" ]; then
    start_docker
elif [ "$STARTUP_TYPE" = "local" ]; then
    start_local
else
    echo "Unknown startup type: $STARTUP_TYPE. Possible values ($ENV_FILE_NAME): docker / local"
    exit 1
fi