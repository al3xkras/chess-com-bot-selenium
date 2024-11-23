# shellcheck disable=SC2164
cd ./docker
docker compose stop
docker compose up -d --build
# sleep 3
# python3 -m webbrowser "http://localhost:7900"
