cd ./docker
docker-compose stop
docker-compose up -d
timeout 3
python -m webbrowser "http://localhost:7900"
