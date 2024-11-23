cd ./docker
docker compose stop
docker compose up -d --build
timeout 3
python3 -m webbrowser "http://localhost:7901"
