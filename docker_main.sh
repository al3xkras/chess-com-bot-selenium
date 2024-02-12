# shellcheck disable=SC2164
cd ./docker
docker-compose stop
docker-compose up -d
sleep 3
python -m webbrowser "http://localhost:7900"
